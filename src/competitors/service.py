"""
Business logic for competitors, including sub-URL discovery — the
priority-ordered strategy from Section 2:

  1. Check robots.txt — usually contains the sitemap URL
  2. Parse that sitemap via ultimate-sitemap-parser
  3. Check llms.txt — curated LLM-friendly page list, newer standard
  4. Fall back to fixed common paths (/pricing, /features, /blog, /about)

Each step only runs if the previous one returned nothing — this is a
fallback chain, not four mandatory steps.
"""

import uuid

import httpx
from fastapi.concurrency import run_in_threadpool
from usp.tree import sitemap_tree_for_homepage

from src.competitors.exceptions import CompetitorAlreadyExists, SourceDiscoveryFailed
from src.competitors.models import Competitor, CompetitorSource, SourceType
from src.competitors.repository import CompetitorRepository, CompetitorSourceRepository
from src.custom_logging import get_logger

log = get_logger(__name__)

# Used only as the last-resort fallback — Step 4 in the discovery chain.
FALLBACK_PATHS = ["/pricing", "/features", "/blog", "/about"]


class CompetitorService:
    def __init__(
        self,
        competitor_repo: CompetitorRepository,
        source_repo: CompetitorSourceRepository,
    ):
        self.competitor_repo = competitor_repo
        self.source_repo = source_repo

    async def add_competitor(self, user_id: uuid.UUID, name: str, main_url: str) -> Competitor:
        """
        Creates the competitor row, then immediately runs sub-URL
        discovery so the competitor has sources to scrape on its very
        first scheduled or on-demand research run.
        """
        existing = await self.competitor_repo.get_by_name_and_user(user_id, name)
        if existing:
            raise CompetitorAlreadyExists()

        competitor = Competitor(user_id=user_id, name=name, main_url=main_url)
        competitor = await self.competitor_repo.create(competitor)

        discovered_urls = await self.discover_sub_urls(main_url)
        await self.save_discovered_sources(competitor.id, discovered_urls)

        return competitor

    async def discover_sub_urls(self, main_url: str) -> list[tuple[str, str]]:
        """
        Returns a list of (url, source_type) tuples. Tries each step in
        order, returns as soon as one step finds anything — never runs
        all four steps unless every earlier one comes up empty.
        """
        base_url = main_url if main_url.startswith("http") else f"https://{main_url}"

        urls = await self._discover_via_robots_and_sitemap(base_url)
        if urls:
            return urls

        urls = await self._discover_via_llms_txt(base_url)
        if urls:
            return urls

        log.warning("competitor.discovery.fallback_used", url=base_url)
        return [(f"{base_url}{path}", "website") for path in FALLBACK_PATHS]

    async def _discover_via_robots_and_sitemap(self, base_url: str) -> list[tuple[str, str]]:
        """
        Step 1 + 2 combined: robots.txt usually contains a Sitemap:
        directive pointing at sitemap.xml. ultimate-sitemap-parser
        (usp) handles fetching robots.txt itself and walking nested
        sitemap indexes, so we don't parse robots.txt by hand here —
        we just let usp's sitemap_tree_for_homepage do both steps.

        usp is a SYNCHRONOUS library — it makes its own blocking HTTP
        calls under the hood. Calling it directly inside this async
        method would freeze the entire event loop for every other
        request while it runs. run_in_threadpool offloads it to
        a worker thread instead.
        """
        try:
            tree = await run_in_threadpool(sitemap_tree_for_homepage, base_url)
            pages = [page.url for page in tree.all_pages()]
            if not pages:
                return []
            # Cap at 10
            return [(url, "website") for url in pages[:10]]
        except Exception as exc:
            log.info("competitor.discovery.sitemap_unavailable", url=base_url, error=str(exc))
            return []

    async def _discover_via_llms_txt(self, base_url: str) -> list[tuple[str, str]]:
        """
        Step 3: llms.txt is the newer standard (Anthropic, Stripe,
        Cloudflare, Vercel use it) — a curated markdown list of a site's
        most important pages, written for LLM agents specifically.
        Roughly 10% of sites have it as of mid-2026
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{base_url}/llms.txt")
                if response.status_code != 200:
                    return []
                lines = response.text.splitlines()
                urls = [
                    line.strip() for line in lines
                    if line.strip().startswith("http")
                ]
                return [(url, "website") for url in urls[:10]]
        except httpx.RequestError as exc:
            log.info("competitor.discovery.llms_txt_unavailable", url=base_url, error=str(exc))
            return []

    def _to_source_type(self, value: str) -> SourceType:
        try:
            return SourceType(value)
        except ValueError:
            log.warning("discovery.unknown_source_type", source_type=value)
            return SourceType.website
    
    async def save_discovered_sources(
        self, competitor_id: uuid.UUID, discovered: list[tuple[str, str]]
    ) -> list[CompetitorSource]:
        """Converts discovery results into CompetitorSource rows and bulk-inserts them."""
        if not discovered:
            raise SourceDiscoveryFailed()
        
        sources = [
            CompetitorSource(competitor_id=competitor_id, url=url, source_type=self._to_source_type(source_type))
            for url, source_type in discovered
        ]
        return await self.source_repo.bulk_create(sources)

    async def update_competitor(self, competitor: Competitor, updates: dict) -> Competitor:
        """Plain field update — no re-discovery triggered even if main_url changes (post-MVP)."""
        return await self.competitor_repo.update(competitor, updates)

    async def delete_competitor(self, competitor: Competitor) -> None:
        """Deletes sources first, then the competitor itself."""
        await self.competitor_repo.delete(competitor)