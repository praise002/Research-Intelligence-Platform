"""
Serper client — fallback search API, used only when Tavily fails after
all retries (Section 2 — Data Sources).

Unlike Tavily, Serper returns Google search results as URL + title +
short snippet only — no full-content extraction. That's an acceptable
tradeoff for a fallback: the goal is to keep the job alive with partial
data rather than failing outright, not to match Tavily's depth.
"""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.custom_logging import get_logger
from src.exceptions import ServiceError

log = get_logger(__name__)

SERPER_BASE_URL = "https://google.serper.dev"

DATE_RANGE_MAP = {
    "hour": "qdr:h",
    "day": "qdr:d",
    "week": "qdr:w",
    "month": "qdr:m",
    "year": "qdr:y",
}

class SerperClient:
    """Async wrapper around Serper's Google Search API — fallback only."""

    def __init__(self):
        self.api_key = settings.SERPER_API_KEY
        self.client = httpx.AsyncClient(
            base_url=SERPER_BASE_URL,
            timeout=settings.TAVILY_TIMEOUT,  # same timeout budget as Tavily — it's a drop-in fallback
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            },
        )

    @retry(
        stop=stop_after_attempt(2),  # this is already the fallback — don't retry as hard as Tavily
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def search(self, query: str, max_results: int = 5, date_range: str | None = "month") -> list[dict]:
        """
        Run a Serper search and return a list of {url, title, snippet} dicts —
        same shape as TavilyClient.search() so the data_fetcher node can
        swap between them without changing how results are consumed.
        
        date_range: one of "hour", "day", "week", "month", "year", or None
        for no date filter. Maps to Serper's `tbs` parameter.

        USAGE:
            results = await serper.search("Grey fintech pricing 2026")
        """
        payload = {"q": query}
        if date_range is not None:
            if date_range not in DATE_RANGE_MAP:
                raise ValueError(f"Invalid date_range: {date_range!r}. Must be one of {list(DATE_RANGE_MAP)}")
            payload["tbs"] = DATE_RANGE_MAP[date_range]
            
        try:
            response = await self.client.post(
                "/search",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            organic_results = data.get("organic", [])[:max_results]
            return [
                {
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                }
                for item in organic_results
            ]
        except httpx.HTTPStatusError as exc:
            log.error("serper.search.failed", query=query, status=exc.response.status_code)
            raise ServiceError(f"Serper search failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            log.error("serper.search.timeout", query=query, error=str(exc))
            raise ServiceError("Serper search timed out") from exc

    async def close(self):
        """Call during FastAPI/Celery shutdown to close the underlying HTTP connection pool."""
        await self.client.aclose()