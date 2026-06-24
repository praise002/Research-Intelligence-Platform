"""
Apify client — social media monitoring (Section 2). Cheaper than the
official X API ($100/month minimum), uses Apify's pre-built actors for
X, Reddit, and LinkedIn scraping instead.

Less stable than an official API, so every method here is designed to
degrade gracefully — if social data is unavailable, the data_fetcher
node continues with web + news sources rather than failing the job
(see the social media rate limiting edge case in docs/ARCHITECTURE.md).
"""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.custom_logging import get_logger
from src.exceptions import ServiceError

log = get_logger(__name__)

APIFY_BASE_URL = "https://api.apify.com/v2"

# Apify actor IDs — pre-built scrapers, one per platform
TWITTER_ACTOR_ID = "apidojo/tweet-scraper"
REDDIT_ACTOR_ID = "trudax/reddit-scraper-lite"
LINKEDIN_ACTOR_ID = "apimaestro/linkedin-posts-search-scraper"


class ApifyClient:
    """Async wrapper around Apify's actor run API for social scraping."""

    def __init__(self):
        self.api_key = settings.APIFY_API_KEY
        self.client = httpx.AsyncClient(
            base_url=APIFY_BASE_URL,
            timeout=settings.APIFY_TIMEOUT,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    @retry(
        stop=stop_after_attempt(2),  # social scraping is the most fragile source — fail fast
        wait=wait_exponential(multiplier=2, min=2, max=8),
        reraise=True,
    )
    async def _run_actor(self, actor_id: str, run_input: dict) -> list[dict]:
        """
        Shared internal method — runs any Apify actor synchronously and
        returns its dataset items. All three public scrape methods below
        call this with a different actor_id and run_input shape.
        """
        try:
            response = await self.client.post(
                f"/actors/{actor_id}/run-sync-get-dataset-items",
                json=run_input,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 408:
                log.warning("apify.actor.timeout_exceeded", actor_id=actor_id)
                raise ServiceError(f"Apify actor {actor_id} exceeded the 300s sync limit") from exc
            
            log.warning(
                "apify.actor.failed",
                actor_id=actor_id,
                status=exc.response.status_code,
            )
            raise ServiceError(f"Apify actor {actor_id} failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            log.warning("apify.actor.timeout", actor_id=actor_id, error=str(exc))
            raise ServiceError(f"Apify actor {actor_id} timed out") from exc

    async def scrape_twitter(
        self,
        query: str,
        max_results: int = 10,
        min_retweets: int | None = None,
        min_favorites: int | None = None,
        min_replies: int | None = None,
    ) -> list[dict]:
        """
        Scrape recent X (Twitter) posts mentioning the competitor.
        Returns list of dicts: {text, author, url, created_at, retweet_count,
        like_count, reply_count, quote_count}.

        `author` is the @handle parsed from the tweet URL — this actor's
        raw output has no separate author/user object.

        min_retweets / min_favorites / min_replies are optional engagement
        floors (maps to Apify's minimumRetweets/minimumFavorites/minimumReplies).
        Leave unset to get all matching tweets regardless of engagement.

        USAGE:
            posts = await apify.scrape_twitter("Grey fintech complaints")
            posts = await apify.scrape_twitter("Grey fintech complaints", min_retweets=5)
        """
        run_input = {
            "searchTerms": [query],
            "maxItems": max_results,
            "sort": "Latest",
        }
        if min_retweets is not None:
            run_input["minimumRetweets"] = min_retweets
        if min_favorites is not None:
            run_input["minimumFavorites"] = min_favorites
        if min_replies is not None:
            run_input["minimumReplies"] = min_replies

        raw_results = await self._run_actor(TWITTER_ACTOR_ID, run_input)
        print(raw_results)
        return [self._normalize_tweet(item) for item in raw_results]

    @staticmethod
    def _normalize_tweet(item: dict) -> dict:
        url = item.get("url", "")
        parts = url.split("/")
        handle = parts[3] if len(parts) > 3 else None

        return {
            "text": item.get("text"),
            "author": handle,
            "url": url,
            "created_at": item.get("createdAt"),
            "retweet_count": item.get("retweetCount", 0),
            "like_count": item.get("likeCount", 0),
            "reply_count": item.get("replyCount", 0),
            "quote_count": item.get("quoteCount", 0),
        }
    
    async def scrape_reddit(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Scrape Reddit posts and comments mentioning the competitor.
        Returns list of dicts: {title, body, community, url, created_at,
        data_type, username, upvotes}.

        USAGE:
            posts = await apify.scrape_reddit("Grey vs Raenest review")
        """
        run_input = {
            "searches": [query],
            "maxItems": max_results,
            "searchPosts": True,
            "searchComments": False,
        }
        raw_results = await self._run_actor(REDDIT_ACTOR_ID, run_input)
        print(raw_results)
        return [self._normalize_reddit_item(item) for item in raw_results]
    
    @staticmethod
    def _normalize_reddit_item(item: dict) -> dict:
        return {
            "title": item.get("title"),
            "body": item.get("body"),
            "community": item.get("communityName"),
            "url": item.get("url"),
            "created_at": item.get("createdAt"),
            "data_type": item.get("dataType"),
            "username": item.get("username"),
            "upvotes": item.get("upVotes", 0),
        }

    @staticmethod
    def _normalize_reddit_item(item: dict) -> dict:
        return {
            "title": item.get("title"),
            "body": item.get("body"),
            "community": item.get("communityName"),
            "url": item.get("url"),
            "created_at": item.get("createdAt"),
            "data_type": item.get("dataType"),
            "username": item.get("username"),
            "upvotes": item.get("upVotes", 0),
        }

    async def scrape_linkedin(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Scrape LinkedIn posts mentioning the competitor — useful for
        funding announcements, hiring trends, and product launches.
        Returns list of dicts: {text, author_name, author_headline,
        author_profile_url, url, posted_at, timestamp, total_reactions,
        comments, shares, hashtags}.

        USAGE:
            posts = await apify.scrape_linkedin("Grey fintech funding")
        """
        run_input = {
            "keyword": query,
            "sort_type": "relevance",
            "page_number": 1,
            "limit": max_results,
        }
        raw_results = await self._run_actor(LINKEDIN_ACTOR_ID, run_input)
        print(raw_results)
        return [self._normalize_linkedin_post(item) for item in raw_results]

    @staticmethod
    def _normalize_linkedin_post(item: dict) -> dict:
        author = item.get("author") or {}
        posted_at = item.get("posted_at") or {}
        stats = item.get("stats") or {}

        return {
            "text": item.get("text"),
            "author_name": author.get("name"),
            "author_headline": author.get("headline"),
            "author_profile_url": author.get("profile_url"),
            "url": item.get("post_url"),
            "posted_at": posted_at.get("date"),
            "timestamp": posted_at.get("timestamp"),
            "total_reactions": stats.get("total_reactions", 0),
            "comments": stats.get("comments", 0),
            "shares": stats.get("shares", 0),
            "hashtags": item.get("hashtags", []),
        }

    async def close(self):
        """Call during FastAPI/Celery shutdown to close the underlying HTTP connection pool."""
        await self.client.aclose()