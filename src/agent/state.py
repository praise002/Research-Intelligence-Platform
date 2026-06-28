"""
ResearchState — the shared baton passed between every LangGraph node.

Each node reads what previous nodes wrote, adds its own output,
and passes the updated state forward. Think of it as a running
notebook for one research job — every node adds a page.

Field ownership by node:
    router_node         → request_type
    query_generator     → queries
    data_fetcher        → raw_sources
    source_validator    → validated_sources, is_sufficient
    synthesiser         → synthesis_output, loop_count
    evaluator           → quality_score
    report_formatter    → report_content
"""

import uuid
from typing import TypedDict

from src.research.models import JobType


class Queries(TypedDict):
    """
    Structured output from call_query_generator().
    Three channels because each needs a different search tool:
      web    → Tavily /search + /extract
      news   → Tavily /search with topic="news"
      social → Apify (X, Reddit, LinkedIn)
    """
    web: list[str]      # 2 queries — general web search
    news: list[str]     # 1 query  — news and press coverage
    social: list[str]   # 2 queries — social media sentiment


class Source(TypedDict):
    """
    A single piece of scraped content from one URL.
    Populated by data_fetcher, cleaned by input guardrails,
    scored and deduplicated by source_validator.
    """
    url: str
    source_type: str        # "website" | "news" | "social"
    content: str            # raw markdown from Tavily / Apify
    credibility_score: float  # 0.0–1.0, set by source_validator
    summary: str            # set by summariser node, empty until then


class ResearchState(TypedDict):
    """
    Full state passed between all nodes in the LangGraph graph.
    Every field starts as None or empty — nodes populate them
    as the pipeline progresses.

    LangGraph requires TypedDict because it needs to merge partial state updates from each node.
    Each node returns only the fields it changed — LangGraph merges
    those into the running state automatically.
    """
    # Job identity — set once at pipeline entry, never changed
    competitor_id: uuid.UUID        # which competitor is being researched
    competitor_name: str            # used in prompts and cache keys
    competitor_url: str             # main URL for discovery
    user_id: uuid.UUID              # who triggered this job
    job_id: uuid.UUID               # = correlation_id — same UUID in LangSmith, logs, Sentry
    correlation_id: str             # str(job_id) — pre-stringified for logging convenience
    request_type: JobType           # WF1 (scheduled) | WF2 (on_demand) | WF3 (alert_scan)

    # Query generation — populated by query_generator node
    queries: Queries                # web, news, social query lists
    
    # Data collection — populated by data_fetcher node
    raw_sources: list[Source]       # everything fetched, before validation
    
    # Validation — populated by source_validator node
    validated_sources: list[Source]  # credible, deduplicated sources only
    is_sufficient: bool              # True if >= 5 validated sources exist

    # Synthesis loop — populated by synthesiser + evaluator nodes
    # loop_count tracks retries: if quality_score < 4.0, synthesiser
    # runs again with refined queries (max 3 loops total)
    loop_count: int                 # starts at 0, incremented each synthesis attempt
    synthesis_output: str           # raw markdown from call_synthesis()
    quality_score: float            # 0.0–5.0 from call_evaluator()

    # Final output — populated by report_formatter node
    report_content: str             # final structured report (SWOT, trends, summary)
    warnings: list[str]             # e.g. ["Low source count — confidence may be reduced"]