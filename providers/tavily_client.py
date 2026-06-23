"""
Tavily client — primary data collection tool (Section 2). Built specifically
for LLM agents, returns clean markdown directly so the agent pipeline never
has to parse raw HTML.

Three operations used by the agent:
  - search()       → finds relevant URLs + short snippets
  - extract()       → takes URLs, returns full clean markdown (up to 20 per call)
  - map_site()       → discovers all URLs on a domain (sub-URL discovery)

If all retries fail, the data_fetcher node falls back to Serper rather than
failing the whole job — see ServiceError in src/exceptions.py.
"""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.custom_logging import get_logger
from src.exceptions import ServiceError

log = get_logger(__name__)

TAVILY_BASE_URL = "https://api.tavily.com"


class TavilyClient:
    """Async wrapper around the Tavily API — search, extract, and map."""

    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.client = httpx.AsyncClient(
            base_url=TAVILY_BASE_URL,
            timeout=settings.TAVILY_TIMEOUT,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=16),  # 1s → 2s → 4s → ... → 16s
        reraise=True,
    )
    async def search(self, query: str, max_results: int = 5, topic: str = "general", time_range: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None) -> list[dict]:
        """
        Run a Tavily search and return a list of {url, title, snippet} dicts.

        USAGE:
            results = await tavily.search("Grey fintech pricing 2026", topic="news")
        """
        try:
            payload = {
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "topic": topic,
            }

            # Dynamically add optional parameters if provided
            if time_range:
                payload["time_range"] = time_range
            if start_date:
                payload["start_date"] = start_date
            if end_date:
                payload["end_date"] = end_date
            if include_domains:
                payload["include_domains"] = include_domains
            if exclude_domains:
                payload["exclude_domains"] = exclude_domains

            response = await self.client.post(
                "/search",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPStatusError as exc:
            log.error("tavily.search.failed", query=query, status=exc.response.status_code)
            raise ServiceError(f"Tavily search failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            log.error("tavily.search.timeout", query=query, error=str(exc))
            raise ServiceError("Tavily search timed out") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        reraise=True,
    )
    async def extract(self, urls: list[str], query: str | None = None,
        chunks_per_source: int | None = None,
        extract_depth: str = "basic") -> list[dict]:
        """
        Extract clean markdown content from up to 20 URLs in a single call.
        Returns a list of {url, raw_content} dicts — no HTML cleaning needed.

        USAGE:
            content = await tavily.extract(["grey.com/pricing", "grey.com/features"])
        """
        if not urls:
            return []
        try:
            payload = {
                "urls": urls[:20],
                "extract_depth": extract_depth,
                # "timeout": settings.TAVILY_TIMEOUT,
            }
            # Optional query-based chunking & reranking
            if query:
                payload["query"] = query
                if chunks_per_source:
                    payload["chunks_per_source"] = chunks_per_source
            response = await self.client.post(
                "/extract",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPStatusError as exc:
            log.error("tavily.extract.failed", urls=urls, status=exc.response.status_code)
            raise ServiceError(f"Tavily extract failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            log.error("tavily.extract.timeout", urls=urls, error=str(exc))
            raise ServiceError("Tavily extract timed out") from exc

    @retry(
        stop=stop_after_attempt(2),  # cheaper operation, fewer retries needed
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def map_site(self, base_url: str, limit: int = 50,
        max_depth: int = 1,
        exclude_paths: list[str] | None = None,
        instructions: str | None = None) -> list[str]:
        """
        Discover all URLs on a domain — used as a fallback in sub-URL
        discovery (Section 2) when robots.txt/sitemap.xml parsing fails.

        USAGE:
            urls = await tavily.map_site("grey.com", exclude_paths=["/blog/.*"])
        """
        try:
            payload = {
                "url": base_url,
                "limit": limit,
                "max_depth": max_depth,
            }
            if exclude_paths:
                payload["exclude_paths"] = exclude_paths
            if instructions:
                payload["instructions"] = instructions

            response = await self.client.post(
                "/map",
                json=payload,
                timeout=120.0, # Override the default client timeout specifically for sitemaps
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPStatusError as exc:
            log.error("tavily.map.failed", base_url=base_url, status=exc.response.status_code)
            raise ServiceError(f"Tavily map failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            log.error("tavily.map.timeout", base_url=base_url, error=str(exc))
            raise ServiceError("Tavily map timed out") from exc

    async def close(self):
        """Call during FastAPI/Celery shutdown to close the underlying HTTP connection pool."""
        await self.client.aclose()