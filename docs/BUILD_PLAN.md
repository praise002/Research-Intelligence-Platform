# ARCIP — MVP Build Plan

Build progress tracker. Check off each step as completed.

---

## Phase 1: Core Infrastructure & Configuration

- [X] **1.1** Create `src/config.py` — Pydantic Settings for all env vars
  - ANTHROPIC_API_KEY, OPENAI_ROUTER_API_KEY, GEMINI_API_KEY
  - TAVILY_API_KEY, SERPER_API_KEY, APIFY_API_KEY
  - RESEND_API_KEY, LANGSMITH_API_KEY
  - DATABASE_URL, REDIS_URL
  - ALLOWED_ORIGINS, ENVIRONMENT, LOG_LEVEL
  - Model names, retry counts, timeout values, TTL constants

- [X] **1.2** Create `src/core/logging.py` — Structlog JSON logger setup
  - Async-safe logging configuration
  - JSON renderer for production, console renderer for dev
  - Correlation ID tracking per request and Celery task

- [X] **1.3** Create `src/core/exceptions.py` — Custom exception hierarchy
  - ARCIPException (base)
  - AuthError, NotFoundError, RateLimitError
  - ResearchJobError, AgentError, SynthesisError
  - GuardrailError, ValidationError, ScheduleError

- [X] **1.4** Create `src/core/errors.py` — Global error codes
  - Map exceptions → structured error JSON
  - Global error codes shared across all modules

---

## Phase 2: Database Setup

- [X] **2.1** Create `src/database.py` — Async SQLAlchemy engine
  - Async engine with SQLModel
  - Session factory with connection pool (max 20 connections)
  - pool_pre_ping=True for connection health checks

- [X] **2.2** Create all SQLModel table models
  - `src/auth/models.py` — User table
  - `src/competitors/models.py` — Competitor, CompetitorSource tables
  - `src/reports/models.py` — Report, Feedback tables
  - `src/alerts/models.py` — Alert table
  - `src/research/models.py` — Job table
  - `src/schedule/models.py` — Schedule table

- [X] **2.3** Set up Alembic for migrations
  - `alembic init -t async migrations`
  - Configure `alembic.ini` with async engine
  - Set file template: `%%(year)d-%%(month).2d-%%(day).2d_%%(slug)s`
  - Generate and run initial migration for all tables

- [X] **2.4** Create `src/repositories/base_repository.py`
  - Abstract base CRUD class — create, get_by_id, update, delete, list
  - All module repositories inherit from this
  - Async SQLAlchemy session injection via dependency

---

## Phase 3: External Service Providers

- [X] **3.1** Create `src/providers/tavily_client.py`
  - Tavily API client wrapper
  - Methods: search(query), extract(urls), map_site(url)
  - Tenacity retry (3 attempts, exponential backoff 1s → 2s → 4s)
  - Fallback flag when Tavily fails — triggers Serper fallback

- [X] **3.2** Create `src/providers/apify_client.py`
  - Apify client for social media scraping
  - Methods: scrape_twitter(query), scrape_reddit(query), scrape_linkedin(query)
  - Tenacity retry (3 attempts)
  - Graceful degradation — continue without social data if unavailable

- [X] **3.3** Create `src/providers/llm_client.py`
  - OpenRouter client — single interface for all models
  - Methods: call_synthesis(prompt), call_evaluator(prompt), call_router(prompt), call_query_generator(prompt)
  - Model mapping: synthesis → Claude Sonnet 4.6, evaluator → Gemini 2.5 Flash, router/query → Claude Haiku
  - Fallback chain: primary model → DeepSeek V3 on failure
  - Tenacity retry on 429 and 500 errors

- [X] **3.4** Create `src/providers/redis_client.py`
  - Redis async client
  - Methods: get(key), set(key, value, ttl), delete(key), exists(key)
  - TTL constants: NEWS_TTL = 86400 (24hrs), WEBSITE_TTL = 604800 (7 days)
  - Connection pool configuration

---

## Phase 4: Middleware & Request Handling

- [X] **4.2** Create `src/middleware/cors.py`
  - CORS middleware with ALLOWED_ORIGINS whitelist
  - Allow React frontend URL only

- [X] **4.3** Create `src/middleware/request_logging.py`
  - Log each request: method, path, user_id, correlation_id
  - Log response: status code, duration_ms
  - Attach correlation ID to request.state for downstream tracing

- [ ] **4.4** Create `src/utils/correlation.py`
  - generate_correlation_id() — UUID4 per request and Celery task
  - Propagate correlation ID from FastAPI → Celery → LangGraph nodes → LangSmith

- [X] **4.5** Create `src/utils/cache.py`
  - Redis cache helpers: get_cached, set_cached, invalidate
  - TTL constants imported from redis_client
  - Cache key builder: build_cache_key(competitor_name, source_type, date)

- [X] **4.6** Create `src/utils/pagination.py`
  - Shared pagination: skip, limit params
  - PaginatedResponse schema — used by reports, alerts, admin logs

---

## Phase 5: Auth Module

- [ ] **5.1** Create `src/auth/schemas.py`
  - GoogleAuthRequest (google_token)
  - TokenResponse (access_token, token_type, user)
  - UserResponse (id, email, name, company, plan)

- [ ] **5.2** Create `src/auth/repository.py`
  - get_user_by_email(email) → User | None
  - create_user(email, name, company) → User
  - Inherits from base_repository

- [ ] **5.3** Create `src/auth/service.py`
  - verify_google_token(google_token) → Google user payload
  - get_or_create_user(google_payload) → User
  - create_access_token(user_id) → JWT string
  - invalidate_token(token) → void (store in Redis blocklist)

- [ ] **5.4** Create `src/auth/dependencies.py`
  - get_current_user() — decode JWT, fetch user from DB
  - Injected into all protected routes via Annotated[User, Depends(...)]

- [ ] **5.5** Create `src/auth/exceptions.py` and `src/auth/errors.py`
  - InvalidToken, UserNotFound, TokenExpired
  - AUTH_001: Invalid token, AUTH_002: User not found, AUTH_003: Token expired

- [ ] **5.6** Create `src/auth/router.py`
  - POST /auth/google — verify Google token, return JWT
  - POST /auth/logout — add token to Redis blocklist

---

## Phase 6: Competitors Module

- [ ] **6.1** Create `src/competitors/schemas.py`
  - CompetitorCreate (name, main_url)
  - CompetitorUpdate (name?, main_url?)
  - CompetitorResponse (id, name, main_url, sources, created_at)
  - SourceResponse (id, url, source_type, last_scraped_at)

- [ ] **6.2** Create `src/competitors/repository.py`
  - CRUD for competitors table
  - CRUD for competitor_sources table
  - get_all_by_user(user_id) → list[Competitor]
  - get_sources_by_competitor(competitor_id) → list[CompetitorSource]

- [ ] **6.3** Create `src/competitors/service.py`
  - add_competitor(user_id, name, main_url) → Competitor
  - discover_sub_urls(main_url) → list[str]
    - Check robots.txt → extract sitemap URL
    - Parse sitemap via ultimate-sitemap-parser
    - Check llms.txt
    - Fall back to fixed common paths (/pricing, /features, /blog, /about)
  - save_discovered_sources(competitor_id, urls) → list[CompetitorSource]
  - update_competitor / delete_competitor

- [ ] **6.4** Create `src/competitors/dependencies.py`
  - valid_competitor_id() — validates competitor exists and belongs to current user
  - Returns competitor or raises CompetitorNotFound

- [ ] **6.5** Create `src/competitors/exceptions.py` and `src/competitors/errors.py`
  - CompetitorNotFound, CompetitorAlreadyExists
  - COMP_001: Not found, COMP_002: Already exists

- [ ] **6.6** Create `src/competitors/router.py`
  - GET /competitors — list all competitors for current user
  - POST /competitors — add competitor + trigger sub-URL discovery
  - GET /competitors/{id} — get one competitor with sources
  - PATCH /competitors/{id} — update competitor
  - DELETE /competitors/{id} — remove competitor and all its sources

---

## Phase 7: Agent — Foundation

- [ ] **7.1** Create `src/agent/state.py` — ResearchState
  - TypedDict with all fields passed between LangGraph nodes:
    - competitor_name, competitor_id, user_id, job_id
    - request_type (WF1, WF2, WF3)
    - queries (web, news, social)
    - raw_sources, validated_sources
    - loop_count (max 3)
    - synthesis_output, quality_score
    - report_content, is_sufficient
    - correlation_id

- [ ] **7.2** Create `src/agent/prompts/` — All 5 prompt templates
  - `router_v1.yaml` — classify request type from job metadata
  - `query_generator_v1.yaml` — generate web, news, social queries with XML tags, role, few-shot examples, tool docs
  - `summarise_v1.yaml` — per-source summarisation (run on each source individually)
  - `synthesise_v1.yaml` — merge all summaries into coherent analysis, evidence before conclusions
  - `evaluate_v1.yaml` — grade report on coverage, accuracy, actionability, structure (1-5 per dimension)

- [ ] **7.3** Create `src/agent/guardrails/input_guards.py`
  - check_prompt_injection(content) — detect and strip instruction-like text from scraped content
  - redact_pii(content) — strip emails, phone numbers, personal names
  - filter_language(content) — discard non-English content
  - check_content_quality(content) — truncate oversized, score relevance, discard low quality
  - run_all_input_guards(sources) → cleaned_sources

- [ ] **7.4** Create `src/agent/guardrails/output_guards.py`
  - check_minimum_length(report) — under 500 words → fail
  - check_source_citations(report) — zero citations → fail
  - check_required_sections(report) — SWOT, trends, summary must exist → fail if missing
  - check_source_count(source_count) — under 5 → add confidence warning
  - run_all_output_guards(report, source_count) → (passed: bool, warnings: list)

---

## Phase 8: Agent — Nodes

- [ ] **8.1** Create `src/agent/nodes/router_node.py`
  - classify_request(state) → state with request_type set
  - Uses Claude Haiku — fast and cheap
  - Loads router_v1.yaml prompt
  - Returns WF1 (scheduled), WF2 (on-demand), WF3 (alert scan)

- [ ] **8.2** Create `src/agent/nodes/query_generator.py`
  - generate_queries(state) → state with queries set
  - Uses Claude Haiku
  - Loads query_generator_v1.yaml
  - Generates web_queries (2), news_queries (1), social_queries (2)
  - Different query style per type — web vs news vs social
  - Injects competitor_name and request_type as prompt variables

- [ ] **8.3** Create `src/agent/nodes/data_fetcher.py`
  - fetch_all_sources(state) → state with raw_sources set
  - Runs three fetchers in parallel using asyncio.gather():
    - fetch_web_sources() — Tavily /search + /extract on returned URLs
    - fetch_news_sources() — Tavily /search with news filter
    - fetch_social_sources() — Apify Twitter + Reddit scrapers
  - Check Redis cache before every API call — serve cached if within TTL
  - Store fresh results in Redis with correct TTL
  - Graceful degradation — if social fails, continue with web + news

- [ ] **8.4** Create `src/agent/nodes/source_validator.py`
  - validate_sources(state) → state with validated_sources set
  - Heuristic credibility scoring per source:
    - Known credible domains (TechCrunch, Reuters) → high score
    - Source is recent (within 90 days) → bonus score
    - Competitor name mentioned in content → relevance bonus
    - Score below threshold → discard
  - Deduplication via pgvector cosine similarity — discard if similarity > 0.92
  - Set state.is_sufficient = True if validated_sources >= 5

- [ ] **8.5** Create `src/agent/nodes/synthesiser.py`
  - synthesise_report(state) → state with synthesis_output set
  - Step 1: Summarise each source individually using Claude Haiku (parallel, cheap)
    - Load summarise_v1.yaml
  - Step 2: Merge all summaries into full analysis using Claude Sonnet 4.6
    - Load synthesise_v1.yaml
    - Run input guardrails on all sources before synthesis
    - Inject summaries into prompt via XML tags

- [ ] **8.6** Create `src/agent/nodes/evaluator.py`
  - evaluate_report(state) → state with quality_score set
  - Uses Gemini 2.5 Flash — different model from synthesiser (cross-model evaluation)
  - Load evaluate_v1.yaml
  - Scores four dimensions 1-5: coverage, accuracy, actionability, structure
  - Average score → quality_score
  - Sets state for routing: score >= 4.0 → proceed, score < 4.0 → refine

- [ ] **8.7** Create `src/agent/nodes/report_formatter.py`
  - format_final_report(state) → state with report_content set
  - Structures output into:
    - Executive Summary (short paragraph, most important insight)
    - SWOT Analysis (4 quadrants with source citations)
    - Trends (patterns over time with citations)
    - Sources list (numbered, with URLs)
  - Runs output guardrails
  - Adds confidence warning if source_count < 5

---

## Phase 9: Agent — LangGraph Graph

- [ ] **9.1** Create `src/agent/graph.py` — LangGraph state machine
  - Define all nodes: router → query_generator → data_fetcher → source_validator → synthesiser → evaluator → report_formatter
  - Define conditional edges:
    - After source_validator: is_sufficient? → synthesiser : query_generator (loop, max 3)
    - After evaluator: score >= 4.0? → report_formatter : synthesiser (refine, max 2)
  - Loop counter logic — increment loop_count, stop at 3
  - Compile graph with checkpointer (Redis or PostgreSQL)
  - Expose run_research(competitor_name, request_type, user_id, job_id) → report_content

---

## Phase 10: Celery Tasks

- [ ] **10.1** Create `src/tasks/celery_app.py`
  - Celery app init with Redis broker
  - Beat schedule — reads from schedules table via celery-sqlalchemy-scheduler
  - Worker configuration: acks_late=True, prefetch_multiplier=1
  - Task routing — research tasks to research queue, alert tasks to alert queue

- [ ] **10.2** Create `src/tasks/research_task.py`
  - @celery.task(bind=True, max_retries=3) run_research_job(competitor_id, user_id, job_id, request_type)
  - Update job status to running in PostgreSQL
  - Run agent graph: await run_research(competitor_name, request_type, user_id, job_id)
  - Save report to PostgreSQL via reports repository
  - Trigger email delivery via Resend
  - Update job status to completed
  - On failure: retry with exponential backoff, update job status to failed on max retries

- [ ] **10.3** Create `src/tasks/alert_task.py`
  - @celery.task run_alert_scan(competitor_id, user_id)
  - Run lightweight research scan — WF3 request type
  - Compare results against last report baseline stored in PostgreSQL
  - If significant delta detected (pricing, feature, news):
    - Create alert record in PostgreSQL
    - Send email notification via Resend
  - Significant delta defined as: new pricing info, new feature mention, major news coverage

- [ ] **10.4** Create `src/tasks/scheduler_task.py`
  - @celery.task dispatch_scheduled_jobs()
  - Run every 5 minutes via Celery beat
  - Read all active schedules from PostgreSQL
  - Group companies in batches of 10
  - Stagger each group by 5 minutes using Celery ETA
  - For each company — spawn one research_task per competitor
  - Skip if company's last job was within schedule frequency window

- [ ] **10.5** Create `src/tasks/cleanup_task.py`
  - @celery.task nightly_cleanup()
  - Run every night at 2am via Celery beat
  - DELETE reports older than 12 months from PostgreSQL
  - DELETE completed jobs older than 90 days
  - Log cleanup stats via Structlog

---

## Phase 11: Reports Module

- [ ] **11.1** Create `src/reports/schemas.py`
  - ReportResponse (id, competitor_name, status, created_at, delivered_at, sources_count)
  - ReportDetail (all above + content, quality_score)
  - FeedbackCreate (rating: int 1-5, comment: str optional)
  - FeedbackResponse (id, rating, comment, created_at)

- [ ] **11.2** Create `src/reports/repository.py`
  - get_all_by_user(user_id, skip, limit) → list[Report]
  - get_by_id(report_id) → Report | None
  - create_report(user_id, competitor_id, content, quality_score, sources_count) → Report
  - update_status(report_id, status, delivered_at) → Report
  - create_feedback(report_id, user_id, rating, comment) → Feedback
  - get_feedback(report_id) → Feedback | None

- [ ] **11.3** Create `src/reports/service.py`
  - get_user_reports(user_id, skip, limit) → list[ReportResponse]
  - get_report_detail(report_id, user_id) → ReportDetail
  - submit_feedback(report_id, user_id, rating, comment) → FeedbackResponse

- [ ] **11.4** Create `src/reports/dependencies.py`
  - valid_report_id() — validates report exists and belongs to current user

- [ ] **11.5** Create `src/reports/exceptions.py` and `src/reports/errors.py`
  - ReportNotFound, FeedbackAlreadySubmitted
  - RPT_001: Not found, RPT_002: Feedback already submitted

- [ ] **11.6** Create `src/reports/router.py`
  - GET /reports — paginated list of reports for current user
  - GET /reports/{id} — full report detail with content
  - POST /reports/{id}/feedback — submit star rating and comment
  - GET /reports/{id}/feedback — get feedback for a report

---

## Phase 12: Alerts Module

- [ ] **12.1** Create `src/alerts/schemas.py`
  - AlertResponse (id, competitor_name, signal_type, content, created_at)
  - AlertDetail (all above + delivered_at)

- [ ] **12.2** Create `src/alerts/repository.py`
  - get_all_by_user(user_id, skip, limit) → list[Alert]
  - get_by_id(alert_id) → Alert | None
  - create_alert(user_id, competitor_id, signal_type, content) → Alert
  - mark_delivered(alert_id, delivered_at) → Alert

- [ ] **12.3** Create `src/alerts/service.py`
  - get_user_alerts(user_id, skip, limit) → list[AlertResponse]
  - get_alert_detail(alert_id, user_id) → AlertDetail

- [ ] **12.4** Create `src/alerts/dependencies.py`
  - valid_alert_id() — validates alert exists and belongs to current user

- [ ] **12.5** Create `src/alerts/exceptions.py` and `src/alerts/errors.py`
  - AlertNotFound
  - ALT_001: Not found

- [ ] **12.6** Create `src/alerts/router.py`
  - GET /alerts — paginated list of alerts for current user
  - GET /alerts/{id} — alert detail

---

## Phase 13: Research Module

- [ ] **13.1** Create `src/research/schemas.py`
  - ResearchTriggerRequest (competitor_id, report_type: optional)
  - ResearchTriggerResponse (job_id, status, message)
  - JobResponse (id, competitor_name, job_type, status, started_at, completed_at)

- [ ] **13.2** Create `src/research/repository.py`
  - create_job(user_id, competitor_id, job_type) → Job
  - update_job_status(job_id, status, celery_task_id) → Job
  - get_job_by_id(job_id) → Job | None
  - get_jobs_by_user(user_id) → list[Job]

- [ ] **13.3** Create `src/research/service.py`
  - trigger_research(user_id, competitor_id) → ResearchTriggerResponse
    - Check rate limit — max 10 on-demand jobs per user per day (Redis counter)
    - Create job record in PostgreSQL
    - Dispatch research_task to Celery with job_id
    - Return job_id and status immediately (async — don't wait for result)

- [ ] **13.4** Create `src/research/dependencies.py`
  - valid_research_request() — check rate limit before allowing trigger

- [ ] **13.5** Create `src/research/exceptions.py` and `src/research/errors.py`
  - RateLimitExceeded, ResearchJobFailed
  - RES_001: Rate limit exceeded (10 jobs/day), RES_002: Job failed

- [ ] **13.6** Create `src/research/router.py`
  - POST /research/trigger — validate request, dispatch Celery task, return job_id immediately

---

## Phase 14: Schedule Module

- [ ] **14.1** Create `src/schedule/schemas.py`
  - ScheduleResponse (id, frequency, day_of_week, time, timezone, status, updated_at)
  - ScheduleUpdate (frequency?, day_of_week?, time?, timezone?, status?)

- [ ] **14.2** Create `src/schedule/repository.py`
  - get_by_user(user_id) → Schedule | None
  - create_schedule(user_id, frequency, day_of_week, time, timezone) → Schedule
  - update_schedule(user_id, updates) → Schedule
  - get_all_active() → list[Schedule] — used by scheduler_task

- [ ] **14.3** Create `src/schedule/service.py`
  - get_user_schedule(user_id) → ScheduleResponse
  - update_user_schedule(user_id, updates) → ScheduleResponse

- [ ] **14.4** Create `src/schedule/exceptions.py` and `src/schedule/errors.py`
  - ScheduleNotFound
  - SCH_001: Not found

- [ ] **14.5** Create `src/schedule/router.py`
  - GET /schedule — get current user's schedule settings
  - PATCH /schedule — update frequency, time, timezone, pause or resume

---

## Phase 15: Profile Module

- [ ] **15.1** Create `src/profile/schemas.py`
  - ProfileResponse (id, name, email, company, plan, created_at)
  - ProfileUpdate (name?, company?)

- [ ] **15.2** Create `src/profile/repository.py`
  - get_by_user_id(user_id) → User | None
  - update_profile(user_id, name?, company?) → User

- [ ] **15.3** Create `src/profile/service.py`
  - get_profile(user_id) → ProfileResponse
  - update_profile(user_id, updates) → ProfileResponse

- [ ] **15.4** Create `src/profile/exceptions.py` and `src/profile/errors.py`
  - ProfileNotFound
  - PRF_001: Not found

- [ ] **15.5** Create `src/profile/router.py`
  - GET /profile — view current user's profile
  - PATCH /profile — update name or company

---

## Phase 16: Admin Module

- [ ] **16.1** Create `src/admin/schemas.py`
  - LogResponse (id, user_id, competitor_name, job_type, status, started_at, completed_at, duration_seconds)
  - LogFilter (status?, job_type?, competitor_id?, date_from?, date_to?)

- [ ] **16.2** Create `src/admin/repository.py`
  - get_all_jobs(filters, skip, limit) → list[Job]
  - get_job_stats() → dict (total, succeeded, failed, avg_duration)

- [ ] **16.3** Create `src/admin/service.py`
  - get_logs(filters, skip, limit) → list[LogResponse]

- [ ] **16.4** Create `src/admin/dependencies.py`
  - is_admin() — check user.plan == "admin" or specific admin flag
  - Raises UnauthorizedAccess if not admin

- [ ] **16.5** Create `src/admin/exceptions.py` and `src/admin/errors.py`
  - UnauthorizedAccess
  - ADM_001: Unauthorized

- [ ] **16.6** Create `src/admin/router.py`
  - GET /admin/logs — paginated job logs with filters

---

## Phase 17: Email Delivery (Resend)

- [ ] **17.1** Create `src/reports/providers/resend_client.py`
  - Resend API client — used only by reports and alerts modules
  - Methods:
    - send_report_email(user_email, report_content, competitor_name) → bool
    - send_alert_email(user_email, alert_content, signal_type, competitor_name) → bool
  - Retry on failure (2 attempts)
  - Log delivery success/failure via Structlog

---

## Phase 18: FastAPI Main Application

- [ ] **18.1** Create/update `src/main.py`
  - FastAPI app initialization with lifespan
  - Register all middleware: CORS, auth, request logging
  - Include all routers with correct prefixes and tags:
    - /auth, /competitors, /reports, /alerts, /research, /schedule, /profile, /admin
  - Register all exception handlers from core/exception_handlers.py
  - Lifespan startup: test DB connection, test Redis connection, warm up LLM client
  - Lifespan shutdown: close DB pool, close Redis connection
  - Hide /docs in production — show only in local and staging

---

## Phase 19: Testing

- [ ] **19.1** Create `tests/conftest.py`
  - Pytest fixtures for async tests
  - Async test client using httpx AsyncClient + ASGITransport
  - DB fixtures — test database with rollback after each test
  - Auth fixture — fake get_current_user via dependency_overrides
  - Redis fixture — mock Redis client

- [ ] **19.2** Create `tests/unit/test_query_generator.py`
  - Test web, news, social queries are generated separately
  - Test query count — 2 web, 1 news, 2 social
  - Test competitor name appears in all queries
  - Test different output for WF1 vs WF2 vs WF3

- [ ] **19.3** Create `tests/unit/test_source_validator.py`
  - Test credibility scoring — known domains score higher
  - Test recency bonus — old articles score lower
  - Test deduplication — similar sources discarded
  - Test is_sufficient flag — set correctly at 5+ sources

- [ ] **19.4** Create `tests/unit/test_guardrails.py`
  - Test prompt injection detection — strips instruction-like text
  - Test PII redaction — removes emails and phone numbers
  - Test language filter — discards non-English content
  - Test output length check — under 500 words fails
  - Test required sections check — missing SWOT fails
  - Test confidence warning — added when source_count < 5

- [ ] **19.5** Create `tests/unit/test_router_node.py`
  - Test WF1 classification — scheduled job
  - Test WF2 classification — on-demand trigger
  - Test WF3 classification — alert scan
  - Test edge cases — ambiguous request types

- [ ] **19.6** Create `tests/unit/test_repositories.py`
  - Test CRUD operations for each module with mocked DB session
  - Test base_repository methods — create, get_by_id, update, delete

- [ ] **19.7** Create `tests/integration/test_research_endpoint.py`
  - POST /research/trigger — returns job_id immediately
  - POST /research/trigger — rate limit exceeded → 429
  - POST /research/trigger — invalid competitor_id → 404
  - Verify Celery task dispatched (mocked)

- [ ] **19.8** Create `tests/integration/test_reports_endpoint.py`
  - GET /reports — returns paginated list
  - GET /reports/{id} — returns full report detail
  - GET /reports/{id} — wrong user → 404
  - POST /reports/{id}/feedback — submit rating successfully
  - POST /reports/{id}/feedback — duplicate submission → 400

- [ ] **19.9** Create `tests/integration/test_alerts_endpoint.py`
  - GET /alerts — returns paginated list
  - GET /alerts/{id} — returns alert detail
  - GET /alerts/{id} — wrong user → 404

---

## Phase 20: Evaluation Setup

- [ ] **20.1** Build golden dataset
  - Create `evals/golden_dataset/competitors.json`
    - Add known public facts about Grey and Raenest (pricing, features, social presence)
    - At least 10 verifiable facts per competitor
  - Create `evals/golden_dataset/expected_reports/grey_expected.md`
  - Create `evals/golden_dataset/expected_reports/raenest_expected.md`

- [ ] **20.2** Create `evals/ragas/ragas_config.yaml`
  - Set thresholds: faithfulness >= 0.90, relevance >= 0.85, precision >= 0.80, recall >= 0.75

- [ ] **20.3** Create `evals/ragas/run_ragas.py`
  - Load golden dataset
  - Run platform against golden dataset (5 research jobs)
  - Compute RAGAS metrics
  - Print pass/fail per metric against thresholds
  - Log results to evals/results/

- [ ] **20.4** Create `evals/prompts/run_promptfoo.yaml`
  - Test each prompt in agent/prompts/ against sample inputs
  - Assert output contains required XML sections
  - Assert no hallucinated competitor names in output

---

## Phase 21: Deployment & DevOps

- [ ] **21.1** Create `Dockerfile`
  - Python 3.11-slim base
  - Install dependencies from requirements.txt
  - Copy src/ only
  - HEALTHCHECK on /health endpoint every 30s
  - CMD: uvicorn src.main:app --host 0.0.0.0 --port 8000

- [ ] **21.2** Create `docker-compose.yml` — local dev only
  - Services: fastapi, celery-worker, celery-beat, redis, postgres, flower, adminer
  - Environment variables from .env file
  - Volume mounts for live reload in development

- [ ] **21.3** Update `.env.example`
  - All required environment variables with descriptions and example values
  - Group by: LLM APIs, Data APIs, Infrastructure, App Config

- [ ] **21.4** Create `railway.json`
  - Railway service configuration
  - Health check path: /health
  - Restart policy on failure

- [ ] **21.5** Create `.github/workflows/ci.yml` — GitHub Actions
  - Trigger on every pull request
  - Steps: install deps → ruff lint → pytest unit tests → pytest integration tests → Docker build smoke test
  - Block merge if any step fails

- [ ] **21.6** Create `Makefile`
  - `make dev` — run FastAPI locally with uvicorn reload
  - `make worker` — run Celery worker locally
  - `make beat` — run Celery beat locally
  - `make test` — run full test suite
  - `make lint` — ruff check + format
  - `make migrate` — run Alembic migrations
  - `make build` — build Docker image

---

## Phase 22: Observability

- [ ] **22.1** Add Structlog events to all key operations
  - research.job.started, research.job.completed, research.job.failed
  - agent.loop.iteration, agent.sources.collected, agent.synthesis.started
  - alert.detected, alert.sent, report.delivered
  - llm.call.made, llm.tokens.used, llm.fallback.triggered
  - cache.hit, cache.miss, cache.set

- [ ] **22.2** Configure LangSmith tracing
  - Set LANGSMITH_API_KEY and LANGCHAIN_TRACING_V2=true in Railway env vars
  - Auto-traces all LLM calls: input, output, tokens, cost, latency
  - Tag each trace with correlation_id and competitor_name for filtering

- [ ] **22.3** Set up cost tracking
  - Log input_tokens, output_tokens, model, cost_usd per LLM call to PostgreSQL
  - Daily cost rollup via Celery beat — aggregate spend per user and per model
  - Alert at $400/month — Structlog warning + (post-MVP: Slack webhook)

---

## Phase 23: Documentation

- [ ] **23.1** Update `docs/ARCHITECTURE.md` with actual implemented flow
- [ ] **23.2** Update `docs/API.md` with live endpoint examples and response schemas
- [ ] **23.3** Update `docs/DATABASE.md` with final schema after migrations
- [ ] **23.4** Update `docs/DEPLOYMENT.md` with Railway setup steps and env var list
- [ ] **23.5** Update `docs/PROMPTS.md` with final prompt decisions and versioning
- [ ] **23.6** Update `docs/EVALUATION.md` with RAGAS results and golden dataset guide
- [ ] **23.7** Update `docs/GUARDRAILS.md` with implemented guardrail logic
- [ ] **23.8** Update `docs/DECISIONS.md` with key decisions made during build

---

## Dependencies & Critical Path

```
Start here:
  1.1 → 1.2 → 1.3 → 1.4 → 1.5 (Core)
    ↓
  2.1 → 2.2 → 2.3 → 2.4 (Database)
    ↓
  3.1 → 3.2 → 3.3 → 3.4 (Providers)
    ↓
  4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 (Middleware & Utils)
    ↓
  5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 (Auth) ← required before all other modules
    ↓
  6.1 → 6.2 → 6.3 → 6.4 → 6.5 → 6.6 (Competitors) ← required before agent
    ↓
  7.1 → 7.2 → 7.3 → 7.4 (Agent Foundation)
    ↓
  8.1 → 8.2 → 8.3 → 8.4 → 8.5 → 8.6 → 8.7 (Agent Nodes) ← can be parallel
    ↓
  9.1 (LangGraph Graph) ← ties all nodes together
    ↓
  10.1 → 10.2 → 10.3 → 10.4 → 10.5 (Celery Tasks)
    ↓
  11 → 12 → 13 → 14 → 15 → 16 (Feature Modules) ← can be parallel
    ↓
  17 (Email delivery)
    ↓
  18.1 (Main App) ← ties everything together
    ↓
  19.1 → 19.2 → ... → 19.9 (Tests)
    ↓
  20.1 → 20.2 → 20.3 → 20.4 (Evals)
    ↓
  21.1 → 21.2 → 21.3 → 21.4 → 21.5 → 21.6 (Deploy)

Parallel tracks (non-blocking):
  - 22 (Observability) — add incrementally as you build
  - 23 (Docs) — update as you go, not at the end
```

---

## Recommended Build Order

**Day 1-2: Foundation**
- Do: 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 2.1 → 2.2 → 2.3 → 2.4

**Day 3-4: Providers & Middleware**
- Do: 3.1 → 3.2 → 3.3 → 3.4 → 4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6

**Day 5: Auth & Competitors**
- Do: 5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 6.1 → 6.2 → 6.3 → 6.4 → 6.5 → 6.6

**Day 6-7: Agent Foundation & Nodes**
- Do: 7.1 → 7.2 → 7.3 → 7.4 → 8.1 → 8.2 → 8.3 → 8.4

**Day 8: Agent Nodes (continued) & Graph**
- Do: 8.5 → 8.6 → 8.7 → 9.1

**Day 9: Celery Tasks**
- Do: 10.1 → 10.2 → 10.3 → 10.4 → 10.5

**Day 10: Feature Modules**
- Do: 11 → 12 → 13 → 14 → 15 → 16 → 17 (run in parallel where possible)

**Day 11: Main App & Tests**
- Do: 18.1 → 19.1 → 19.2 → 19.3 → 19.4 → 19.5 → 19.6

**Day 12: Integration Tests & Evals**
- Do: 19.7 → 19.8 → 19.9 → 20.1 → 20.2 → 20.3 → 20.4

**Day 13: Deploy**
- Do: 21.1 → 21.2 → 21.3 → 21.4 → 21.5 → 21.6

**Day 14: Observability, Polish & Docs**
- Do: 22.1 → 22.2 → 22.3 → 23.1 → 23.2 → ... → 23.8

---

*Last updated: June 2026 — Author: Praizdev*