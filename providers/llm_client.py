"""
LLM client — two AsyncOpenAI instances, one interface.

OpenAI and Gemini both speak the OpenAI chat completions protocol.
Gemini exposes it at a different base_url — that's the only difference.
No LangChain here. LangChain lives in graph.py and the node definitions
where LangGraph actually needs it.

Model assignment by role:
  - call_synthesis()        → SYNTHESIS_MODEL       — merges sources, writes report
  - call_evaluator()        → EVALUATOR_MODEL        — grades report (Gemini, avoids self-grading bias)
  - call_router()           → ROUTER_MODEL           — classifies WF1 / WF2 / WF3
  - call_query_generator()  → QUERY_GENERATOR_MODEL  — generates 3-5 search queries
  - call_summariser()       → QUERY_GENERATOR_MODEL  — summarises one source before synthesis

Structured output (router + query generator) is handled by prompting the
model to return JSON and validating with Pydantic — works identically on
OpenAI and Gemini without using provider-specific structured output APIs.
"""

from typing import Literal
from pydantic import BaseModel
from openai import AsyncOpenAI, APIStatusError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import settings
from src.custom_logging import get_logger
from src.exceptions import AgentError

log = get_logger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"



# Pydantic models for structured outputs

class RouterOutput(BaseModel):
    workflow: Literal["WF1", "WF2", "WF3"]


class QueryGeneratorOutput(BaseModel):
    web: list[str]     # 2 queries — general web search
    news: list[str]    # 1 query  — news/press
    social: list[str]  # 2 queries — X, Reddit, LinkedIn


# Retry helper

def _is_retryable(exc: APIStatusError) -> bool:
    """Only retry on transient server errors and rate limits. Not on bad requests."""
    return exc.status_code in {429, 500, 502, 503, 504}


# Client

class LLMClient:
    def __init__(self):
        self.openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
        )
        self.gemini_client = AsyncOpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=GEMINI_BASE_URL,
        )

    def _client_for(self, model: str) -> AsyncOpenAI:
        """Pick the right HTTP client based on model name prefix."""
        if model.startswith("gemini-"):
            return self.gemini_client
        return self.openai_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=16),  # 1s → 2s → 4s
        retry=retry_if_exception_type(APIStatusError),
        reraise=True,
    )
    async def _call(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float | None = None,
    ) -> str:
        """
        Single LLM call with retry on transient errors.
        Every public method delegates here — one place to change if the
        completions interface ever shifts.
        """
        client = self._client_for(model)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=max_tokens,
                temperature=temperature or settings.TEMPERATURE,
            )
            return response.choices[0].message.content or ""
        except APIStatusError as exc:
            if not _is_retryable(exc):
                raise  # 400 bad request, bad prompt — don't waste retries
            log.warning("llm.call.failed", model=model, status=exc.status_code)
            raise

    async def _call_with_fallback(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float | None = None,
    ) -> str:
        """
        Tries the primary model (with retries via _call). If exhausted,
        falls back to FALLBACK_MODEL once. If that also fails, raises
        AgentError — triggers a 503 in the API layer.
        """
        try:
            return await self._call(model, system_prompt, user_message, max_tokens, temperature)
        except Exception as exc:
            log.error("llm.primary_model.exhausted", model=model, error=str(exc))
            try:
                return await self._call(
                    settings.FALLBACK_MODEL, system_prompt, user_message, max_tokens, temperature
                )
            except Exception as fallback_exc:
                log.error(
                    "llm.fallback_model.exhausted",
                    model=settings.FALLBACK_MODEL,
                    error=str(fallback_exc),
                )
                raise AgentError() from fallback_exc

    # Public methods — plain string output

    async def call_synthesis(self, system_prompt: str, sources: str) -> str:
        """
        Merges validated sources into the full report.
        Flagship model — best at handling noisy mixed data across 15+ sources.
        """
        return await self._call_with_fallback(
            model=settings.SYNTHESIS_MODEL,
            system_prompt=system_prompt,
            user_message=sources,
            max_tokens=settings.MAX_TOKENS,
        )

    async def call_evaluator(self, system_prompt: str, report: str) -> str:
        """
        Grades report quality. Gemini deliberately — different provider
        from synthesis to avoid the bias of an LLM grading its own work.
        Output is short: a score + brief feedback, not a full report.
        """
        return await self._call_with_fallback(
            model=settings.EVALUATOR_MODEL,
            system_prompt=system_prompt,
            user_message=report,
            max_tokens=512,
        )

    async def call_summariser(self, system_prompt: str, source_content: str) -> str:
        """
        Summarises one source before synthesis. Runs up to 15x per report
        so cost matters — uses the same cheap model as router/query generator.
        """
        return await self._call_with_fallback(
            model=settings.QUERY_GENERATOR_MODEL,
            system_prompt=system_prompt,
            user_message=source_content,
            max_tokens=settings.MAX_TOKENS_SUMMARY,
        )

    # Public methods — structured output (Pydantic)

    async def call_router(self, system_prompt: str, job_metadata: str) -> RouterOutput:
        """
        Classifies the incoming job as WF1 (scheduled), WF2 (on-demand),
        or WF3 (alert scan).

        The system prompt in router_v1.yaml must instruct the model to
        respond ONLY with JSON matching: {"workflow": "WF1" | "WF2" | "WF3"}
        """
        raw = await self._call_with_fallback(
            model=settings.ROUTER_MODEL,
            system_prompt=system_prompt,
            user_message=job_metadata,
            max_tokens=64,
        )
        try:
            return RouterOutput.model_validate_json(raw)
        except Exception as exc:
            log.warning("llm.router.parse_failed", raw=raw, error=str(exc))
            raise AgentError("Router returned unparseable output") from exc

    async def call_query_generator(
        self, system_prompt: str, competitor_context: str
    ) -> QueryGeneratorOutput:
        """
        Generates 3-5 targeted search queries split by channel.

        The system prompt in query_generator_v1.yaml must instruct the model
        to respond ONLY with JSON matching:
        {"web": [...], "news": [...], "social": [...]}
        """
        raw = await self._call_with_fallback(
            model=settings.QUERY_GENERATOR_MODEL,
            system_prompt=system_prompt,
            user_message=competitor_context,
            max_tokens=256,
        )
        try:
            return QueryGeneratorOutput.model_validate_json(raw)
        except Exception as exc:
            log.warning("llm.query_generator.parse_failed", raw=raw, error=str(exc))
            raise AgentError("Query generator returned unparseable output") from exc

    async def close(self):
        """Call during FastAPI/Celery shutdown to drain both connection pools."""
        await self.openai_client.close()
        await self.gemini_client.close()