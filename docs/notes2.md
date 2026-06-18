User: Marketing and product teams
Problem: Hours spent manually tracking competitor moves, results are stale by the time they're done
Key trigger for action: Pricing changes, feature launches, messaging shifts
Data sources: Competitor websites, X, news APIs, G2/Capterra
Report cadence: Weekly scheduled + real-time alert on significant moves
Delivery: Email + dashboard

So our full assumptions list is:
Competitors have a meaningful public online presence
Multiple users monitor the same competitors — caching is viable
Tavily/Serper return enough clean accessible content per query
100 companies at launch — Celery queuing handles the load
Reports are clear and specific enough that users act on them — if not, adoption dies quietly

They're different things:
Constraints are limitations you have to work within — budget, scale, latency, tech stack
Assumptions are things you're betting are true but haven't proven yet
Constraints & Scale
API costs must be managed — Tavily/Serper charge per query
Reports processed asynchronously via Celery — real-time delivery not required
Real-time alerts(notification)
Read/write ratio - read heavy
Data retention: Reports and raw sources kept for 12 months; configurable per org
Tech stack is fixed — LangChain, LangGraph, BeautifulSoup, Tavily/Serper, PostgreSQL, Celery
Expected load — 100 companies at launch, 100 reports/week, 1,500-2,000 source fetches/week
Assumptions:
Competitors have a meaningful public online presence
Multiple users monitor the same competitors — making caching viable
Tavily/Serper return enough clean accessible content per query
Reports are clear and specific enough that users act on them
Competitor data is legally scrapable under robots.txt and ToS
LLM APIs available at 99.9% SLA with GPT-4o fallback
Users comfortable with 15-30 min delay — background processing acceptable
English-language sources only — multi-language is post-MVP
Source credibility uses heuristics — not a trained classifier
Users provide competitor list at onboarding — no auto-discovery


A heuristic is basically a shortcut rule that's good enough without being perfect.
For example:
"If the source is BBC, Reuters, or TechCrunch — it's credible"
"If the domain ends in .edu or .gov — it's credible"
"If 10 other sites link to it — it's probably credible"
These are simple rules a developer writes manually. They work most of the time but not always. A random blogger could get linked by 10 sites and still be unreliable.
The alternative — a trained classifier — would learn credibility from thousands of examples. Much smarter, but takes months to build and data to train it.
Think of it like this: a heuristic is a junior researcher following a checklist. A trained classifier is an experienced editor with years of judgment.

**Success Metrics — Key Decisions**

We kept all 7 metrics from the doc. Here's the reasoning behind each:

**Report generation time < 30 min**
Users are comfortable waiting — research is complex and background processing is the industry standard. Not real-time.

**Source coverage >= 15 unique sources**
A human researcher finds 5-10 sources manually in 30 minutes. Automation justifies 15 as a realistic and meaningful improvement.

**Report quality score >= 4.0/5.0**
LLM-as-judge scores structure, coherence, and coverage. Works best when combined with the hallucination metric below — neither alone is sufficient.

**Hallucination rate < 5%**
An AI judge can't catch confident-sounding wrong claims. So every claim in the report must be cross-referenced back to an actual retrieved source. Quality score and hallucination rate work together.

**Scheduled job success rate >= 99%**
Only achievable with proper retry logic and fallbacks — external dependencies like Tavily, the LLM API, and PostgreSQL can all fail. Retries make 99% realistic.

**Cost per report < $2.00**
At 100 companies running weekly reports, total monthly API cost is ~$800. Combined with ~$700 infrastructure, charging $20-30/month per company makes the business viable.

**User satisfaction >= 80% positive**
Cost and satisfaction must both be true simultaneously. Low cost with low satisfaction means users churn. High satisfaction with high cost means you go broke.

Core workflows:

**WF1 — Scheduled Reports**
Every week (or every day), the platform automatically researches your competitors and sends you a report. You don't have to do anything — it just arrives.

**WF2 — Research on Demand**
If you want a report right now without waiting for the scheduled one, you can request it manually. Like asking "give me a deep dive on Grey right now."

**WF3 — Real-Time Alerts**
If something big happens — a competitor drops their price, launches a new feature, or gets major press coverage — you get notified immediately. You don't wait for the weekly report.

**WF4 — Report History**
Every report the platform generates gets saved. You can go back, browse old reports, and search through them. Like an archive of everything the platform has discovered over time.

Edge cases are:
Insufficient public data (merged EC1 + EC5) — partial report with clear user feedback ✅
Paywalled sources — skip and move to next source ✅
Competitor rebrand — flag to user when competitor suddenly returns zero results ✅
Social media rate limiting — retry with backoff, continue with other sources, flag missing X data in report ✅

SWOT stands for:
Strengths — what is the competitor doing well
Weaknesses — where are they struggling
Opportunities — gaps you could exploit
Threats — things they're doing that could hurt you
Trends — patterns spotted over time. For example "Grey has been cutting prices every quarter for 6 months."
Executive Summary — a short paragraph at the top of the report. The busy founder or marketing manager reads only this if they have 2 minutes. It captures the most important insight from the entire report.

So now we have the complete flow:
Celery triggers job → pulls competitor list from PostgreSQL
Router classifies the request type WF1, etc
Parallel workers fan out simultaneously — web scraper, news API, social monitoring
LangGraph evaluates results — good enough or loop again? Max 3 times
Synthesis engine merges and analyses
Report generator produces SWOT, trends, executive summary
Evaluator scores the report — above 4.0 deliver, below 4.0 refine
Deliver via email, save to PostgreSQL

Our model selection criteria are:
Quality — handles noisy, mixed data well
Cost — supports $2.00 per report target
Latency/Speed — contributes to 30 min report target
OpenAI compatible — works with LangChain/LangGraph via OpenRouter
Context window — handles 15+ sources simultaneously

Now with those 5 criteria, here are 4 models worth testing:
Model
Quality
Cost
Speed
Context
Notes
Claude Sonnet 4.6
Excellent
Medium
Fast
200K
Best LangChain integration, proven synthesis
Gemini 2.5 Flash
Very good
Low ($0.30/M)
Very fast
1M
Best value among commercial APIs
DeepSeek V3
Very good
Very low ($0.25/M)
Fast
1M
Open source, frontier quality
Owl Alpha
Unverified
Free
Unknown
1M
Built for agents but no benchmarks yet

Primary synthesis: Claude Sonnet 4.6
Evaluator/judge: Gemini 2.5 Flash
Routing/classification: Claude Haiku or GPT-4o-mini — fast and cheap for simple decisions
Fallback: DeepSeek V3 — if primary models are down or too expensive
Test candidate: Owl Alpha — evaluate during build

So the full testing picture for your agentic system is:
Unit tests — individual components like router, scraper, parser
RAGAS — quality of retrieval and synthesis
Golden dataset — end-to-end against known facts
LangSmith — trace every agent decision in production

So your full tech stack is now confirmed:
Layer
Technology
Reason
Scheduling & workers
Celery + Redis
Parallel collection, job queuing
Research loop
LangGraph + LangChain
Stateful iterative research
Web scraping
BeautifulSoup + Playwright
Static and JS pages
Search/news
Tavily + Serper
Primary and fallback
Social media
Apify
Cheaper than X API
Database
PostgreSQL
Reports, sources, user config
Caching
Redis
Frequent queries, embeddings
Backend
FastAPI
Async, LangChain friendly
LLM - synthesis
Claude Sonnet 4.6
Best noisy data handling
LLM - evaluator
Gemini 2.5 Flash
Cross-model evaluation
LLM - routing
Claude Haiku
Fast, cheap classification
LLM - fallback
DeepSeek V3
Cost backup

Layer
Technology
Reason
Email delivery
Resend
Modern, developer-friendly email API
Deployment (MVP)
Railway
Simple, fast to ship
Deployment (scale)
DigitalOcean
More control, cheaper at volume

Observability has has three parts:
Logs — a record of everything that happened. "Report for Company X started at 9:00am, Tavily returned 12 results, synthesis completed at 9:18am, delivered at 9:21am." Or "Report failed at synthesis step — LLM timeout."
Metrics — numbers tracked over time. How many reports succeeded today? What's the average generation time? How much did the LLM API cost today?
Alerts — notifications when something goes wrong. Error rate spike, cost anomaly, job failure.

observability stack for your platform:
Tool
What it monitors
LangSmith
Every LLM call, agent decisions, token cost
Prometheus + Grafana
Job success rate, generation time, queue depth
Redis monitoring
Cache hit rate, memory usage
Sentry
Real-time error alerts

6 prompt engineering elements are:
XML tags — structure sources clearly
Evidence before conclusions — cite sources before making claims
Specific role — "You are a competitive intelligence analyst"
Step by step reasoning — SWOT first, then trends, then summary
Few shot examples — show it a sample good report
Tool documentation — clear description of what each tool does, parameters, edge cases, example usage

MVP:
XML tags — structure
Evidence before conclusions — fight hallucination
Specific role — identity
Few shot examples — show don't tell
Tool documentation — critical from day one
Post-MVP:
1. Step by step reasoning — add when you notice report structure needs improvement

Anthropic also said — "Start with simple prompts, add complexity only when it demonstrably improves outcomes."

"We actually spent more time optimizing our tools than the overall prompt."


Anthropic's article said — "Success isn't about building the most sophisticated system. It's about building the right system for your needs."

So your caching strategy is:
Cache duration: 24 hours for news and social data — these change daily
Cache duration: 7 days for competitor website data — pricing pages, feature pages
Cache key: competitor name + source type + date
Cache storage: Redis — already in your stack

News and social (X, Reddit) — cache for 24 hours. New articles and posts appear daily
Competitor website data — cache for 7 days. Pricing pages and feature pages rarely change overnight

So your complete caching layer is:
Three levels:
Semantic cache — Redis + LangChain; similar queries return cached results; saves API costs
News/social cache — Redis; 24 hour TTL; X, Reddit, news API results
Website cache — Redis; 7 day TTL; competitor pricing pages, feature pages
TTL just means Time To Live — how long before the cache expires and fresh data is fetched.

Evaluation — happens before and during development. Did my system produce the right output? Runs on test data. You control when it happens.
Monitoring — happens in production continuously. Is my system still performing well over time? Runs on real data. Never stops.



Review reports that fall below a certain quality score threshold.
For your platform specifically:
Score >= 4.0 — deliver automatically, no human review needed
Score 3.0 - 3.9 — flag for human review before delivery
Score < 3.0 — don't deliver, trigger retry, then human review

So your complete human review rubric is:
Accuracy:
Are all claims backed by cited sources — no hallucinations
Are the facts correct and verifiable
Usability:
3. Is it actionable — can a marketing manager do something with it immediately
4. Is it readable — no technical jargon, clear language
That's your 4-point rubric. Reviewers score each dimension 1-5. Average becomes the human review score.

The full loop looks like this:
Report delivered → user feedback (thumbs up/down) → low quality reports flagged → human reviewer scores with rubric → patterns identified → fix prompt, tool, or model → test fix with golden dataset → deploy → repeat
This is why evaluation isn't a one-time thing. It's a continuous cycle.
Anthropic calls this closing the loop — every failure teaches the system something.

So your evaluation process in practice looks like this:
System flags low scoring reports automatically
Beta user (marketer) reviews using 4-point rubric
Weekly meeting — marketer and developer review patterns together
Developer fixes highest frequency issues
Golden dataset confirms fix worked before deploying

So the correct order is:
Golden dataset first — build it manually. Pick 5-10 real competitors, gather known facts about them. This becomes your ground truth.
RAGAS second — run your platform against the golden dataset. Measure faithfulness, relevance, context precision.
Human review last — for reports that pass RAGAS but still feel off to a real user.
Each one catches different problems:
Golden dataset catches factual errors
RAGAS catches retrieval and synthesis quality issues
Human review catches usability and actionability issues
Section 4 is now complete. Here's what we covered:
✅ Evaluation vs monitoring — when each happens
✅ Three evaluation types and correct order
✅ Human review rubric — accuracy + usability
✅ Feedback loop — how failures improve the system
✅ Who owns what — developer + marketer working together

Collection → Guardrail & Cleaning Layer → Merge → Synthesis

Simple rule-based output checks before delivery:
Minimum length check — if report is under 500 words, something went wrong. Don't deliver, trigger retry.
Source citation check — if report contains zero source citations, flag it. Every report must reference at least one source.
Required sections check — does the report contain SWOT, trends, and executive summary? If any section is missing, flag it.
Confidence flag — if fewer than 5 sources were found, add a visible warning to the report: "Limited data available — treat findings with caution."

So your guardrail checks before content reaches the LLM are:
Prompt injection detection — flag and strip instruction-like text from scraped content
Content length and quality filter — truncate oversized content, score relevance, discard low quality
PII redaction — strip personal emails, phone numbers, names from scraped content
Language filter — discard non-English content at MVP

Input: Prompt injection, content quality, PII, language filter
Output: Length, citations, required sections, confidence flagging

Summary:
Input guardrails — before synthesis:
Prompt injection detection — strip instruction-like text from scraped content
Content quality filter — truncate oversized content, discard low relevance
PII redaction — strip personal emails, phone numbers from scraped data
Language filter — discard non-English content at MVP
Output guardrails — before delivery:
Minimum length check — under 500 words triggers retry
Source citation check — zero citations flags for review
Required sections check — SWOT, trends, executive summary must all exist
Confidence flag — fewer than 5 sources adds visible warning to report
Two layer safety net:
Guardrails — fast, cheap, rule-based
Evaluator — slower, semantic, catches hallucination

An error is something that goes wrong that the system can recover from. Tavily returns a 429 rate limit — that's an error. You retry and it works.
A failure is when the system can't recover and gives up. Tavily returns 429, you retry 3 times, still failing — now the job has failed. The user gets no report.
So errors are expected and handled. Failures are the last resort.

Web scraping — extract content from a specific URL you already know. You go to grey.com/pricing and pull the text. That's it.
Web crawling — start at a URL, follow all the links, scrape those pages too, follow their links, and so on. Much more complex.

exponential means each wait time multiplies, so it's actually:
1s → 2s → 4s → 8s → 16s

Tavily gets overloaded. 1000 platforms all get 429 errors. They all retry every 5 seconds simultaneously. Tavily gets hit with another 1000 requests 5 seconds later. Still overloaded. Another 1000 requests 5 seconds later. It never recovers.
Exponential backoff spreads the retries out over time. By the time your platform retries at 16 seconds, other platforms are retrying at different intervals. The traffic spreads out and Tavily recovers.
It's actually considerate engineering — you're not hammering a struggling service.

So your complete error handling strategy is:
External service errors:
Retry with exponential backoff — 1s, 2s, 4s, 8s, 16s
Max 3 retries then fallback — Serper if Tavily fails, continue without X if Apify fails
Deliver partial report with confidence warning if sources are insufficient
Job failures:
4. acks_late=True — job returns to queue if worker crashes
5. State stored in Redis — resume from last checkpoint
6. Idempotent design — no duplicate execution
LLM failures:
7. Retry on 429 and 500 errors with backoff
8. Fallback to DeepSeek V3 if Claude is down
9. Malformed JSON — retry with explicit format reminder, max 3 attempts
Database failures:
10. Connection pool via SQLAlchemy — handles transient failures
11. Circuit breaker — stop hitting PostgreSQL after 5 consecutive failures, alert developer

Without a circuit breaker — PostgreSQL is down, your platform keeps sending requests every second, thousands of failed requests pile up, logs fill up, your whole system slows down trying to connect to a dead database.
With a circuit breaker — after 5 consecutive failures, the circuit trips. Your platform stops trying to hit PostgreSQL entirely. Instead it immediately returns an error. Once PostgreSQL recovers, the circuit resets and normal requests resume.
Three states:
Closed — everything normal, requests flow through
Open — circuit tripped, requests blocked immediately
Half-open — testing if service recovered, let one request through to check
For your platform this means:
5 consecutive PostgreSQL failures → circuit opens → alert sent to developer → no more requests until manual reset or auto-recovery

Section 6 is now complete. Here's the summary:
External service errors:
Exponential backoff retries — spreads load, considerate engineering
Fallbacks for every critical service — Serper, DeepSeek, continue without X
Partial report delivery with confidence warning
Job reliability:
acks_late=True — no lost jobs on worker crash
Redis state storage — resume from checkpoint
Idempotent design — no duplicate execution
LLM failures:
Retry on 429/500 with backoff
Fallback to DeepSeek V3
Malformed JSON retry with format reminder
Database failures:
SQLAlchemy connection pool
Circuit breaker after 5 consecutive failures


SQLModel vs SQLAlchemy
SQLModel is actually built on top of SQLAlchemy — it uses SQLAlchemy under the hood. So connection pooling is still handled the same way, SQLModel just gives you a cleaner interface. Good choice actually — it works well with FastAPI.
Connection pool in simple terms:
Imagine a library with 20 study rooms. 100 students all want a room at the same time. Instead of building 100 rooms, you manage 20 rooms — students queue, use a room, leave, next student enters.
That's a connection pool. 20 database connections shared across 100 jobs. Jobs wait their turn instead of all connecting simultaneously.
Staggered means spreading things out over time.
Instead of all 100 reports triggering at 6:00:00am exactly — you spread them:
Company 1-10 → 6:00am
Company 11-20 → 6:05am
Company 21-30 → 6:10am
And so on...
By the time company 100 starts, company 1 is already halfway done. Load is spread across time instead of hitting all at once.

So your bottlenecks and solutions are:
Bottleneck 1 — LLM rate limits
100 jobs all calling Claude simultaneously hit Anthropic's rate limits. Solution — Celery queue with rate limiting. Stagger LLM calls, don't fire all 100 at once.
Bottleneck 2 — Database connections
100 jobs saving reports simultaneously. Solution — SQLAlchemy connection pool, max 20 connections shared across all workers.
Bottleneck 3 — External API rate limits
100 jobs all hitting Tavily simultaneously. Solution — caching reduces duplicate calls + request queuing.
Bottleneck 4 — Memory
100 jobs each holding 15 sources in memory simultaneously. Solution — process and discard sources after synthesis, don't hold everything in memory.

In Celery beat terms:
Get all 100 companies from PostgreSQL
Split into groups of 10
Schedule each group 5 minutes apart
Celery beat executes each group at its scheduled time
Simple to implement — just a loop that calculates base_time + (group_index * 5 minutes) for each group

One user's 20 minute report blocks everyone else.
With async:
User triggers report
FastAPI immediately returns "Report started, we'll notify you when done"
Celery picks up the job in the background
Other users can trigger their own reports, browse the dashboard, check old reports — all without waiting
When the report finishes, user gets notified via email
The key insight is — the API never waits. It hands off to Celery immediately and stays free to handle other requests.
This is why async + Celery work together. FastAPI handles the HTTP layer without blocking. Celery handles the heavy lifting in the background.

Section 7 complete. Here's the summary:
Scaling approach: Horizontal scaling via Railway/DigitalOcean — add workers on demand
Bottlenecks and solutions:
LLM rate limits → staggered Celery scheduling
Database connections → SQLModel/SQLAlchemy connection pool
External API limits → caching + request queuing
Memory → process and discard sources after synthesis
Performance optimisations:
Async FastAPI — never blocks on long running jobs
Celery background processing — immediate API response
Staggered Monday reports — groups of 10, 5 minutes apart
Semantic caching with pgvector HNSW index — stays fast at scale

Regular caching — stores exact query and result:
Query: "Grey fintech pricing" → stores result
Next time someone searches "Grey fintech pricing" exactly → returns cached result
Different wording = cache miss, fetches fresh data
Semantic caching — stores the meaning, not the exact words:
Query: "Grey fintech pricing" → converts to embedding → stores embedding + result
Next query: "Grey app subscription cost" → converts to embedding → compares with stored embeddings via pgvector → similarity is high → returns same cached result
So yes — you are caching the embedding alongside the result.
Think of an embedding as a list of numbers that represents the meaning of a sentence. Two sentences with similar meaning produce similar numbers.
Stored in Redis or pgvector?
Actually both work together:
pgvector — stores and searches embeddings efficiently
Redis — stores the actual cached API results
pgvector finds which cached query is most similar. Redis returns the stored result for that query.

Section 8 complete. Summary:
Containerisation:
Development — docker-compose.yml with all services including Adminer and Flower
Production — individual Dockerfile, Railway manages services separately
Observability tools:
LangSmith for MVP — cloud hosted, just set env vars
Switch to LangFuse later — open source, self hosted
Prometheus + Grafana — separate Railway services
CI/CD pipeline:
GitHub Actions — tests, PromptFoo, Docker build
Railway — auto-deploy on CI pass, block on failure
Blue-green deployment — gradual traffic shift
One-click rollback for critical bugs
Secrets:
Local — .env file gitignored
Production — Railway environment variables UI

Section 9 complete. Summary:
Debugging flow for a failed report:
Sentry — did it crash with an error?
LangSmith — trace every agent decision via correlation ID
Prometheus/Grafana — was there a broader infrastructure issue?
PostgreSQL — did the report save correctly?
Observability stack:
LangSmith — LLM traces, token costs, quality scores
Prometheus + Grafana — queue depth, latency, success rate
Sentry — error tracking and alerts
Structlog — structured JSON logging throughout
Correlation IDs — one ID traces entire report journey
Cost tracking — token logs, daily rollup, $400 budget alert

Section 10 — Privacy & Compliance Summary
Data stored about users:
Name, email, company name — account data
Competitor list — research preferences
Report history — 12 months retention
Usage logs — billing and debugging
PII handling:
Scraped content checked for PII before reaching synthesis LLM
User account data stored securely in PostgreSQL
API keys stored in Railway environment variables — never in code
Compliance:
GDPR — users can request data export or deletion within 30 days of account closure
CCPA — no user data sold to third parties
robots.txt respected by all scraping workers
LLM Data Retention:
Standard Anthropic API — data kept 30 days, not used for training on commercial plans. Good enough for MVP
ZDR available later — enterprise agreement with Anthropic, inputs and outputs not stored at all
AWS Bedrock/GCP Vertex — alternative route for enterprise data privacy, adds infrastructure complexity
For the project:
Document compliance requirements even if not fully implemented
Shows production awareness which matters for the assignment
Upgrade to ZDR when first enterprise customer requires it — YAGNI principle


database schema with explanations:
users
- id (UUID) — unique identifier
- email (unique) — login and report delivery
- name — display name
- company — their organisation
- plan (free/paid) — billing tier
- created_at

competitors
- id (UUID)
- user_id → users — which user added this competitor
- name — e.g. "Grey"
- main_url — e.g. "grey.com" — user provides this
- created_at

competitor_sources
- id (UUID)
- competitor_id → competitors — which competitor this URL belongs to
- url — discovered sub-URL e.g. "grey.com/pricing"
- source_type (website/social/news/review) — where it came from
- last_scraped_at — when we last fetched this URL
- created_at

reports
- id (UUID)
- user_id → users — who this report belongs to
- competitor_id → competitors — which competitor was researched
- content (text) — full report markdown
- quality_score — internal LLM-as-judge score, not shown to user
- sources_count — how many sources were used
- status (pending/completed/failed) — job state
- created_at
- delivered_at — when email was sent

alerts
- id (UUID)
- user_id → users — who to notify
- competitor_id → competitors — which competitor triggered the alert
- signal_type (pricing/feature/news/social) — what kind of change
- content (text) — short summary of what changed
- delivered_at — when email was sent
- created_at

jobs
- id (UUID) — correlation ID for tracing across LangSmith/logs
- user_id → users
- competitor_id → competitors
- job_type (scheduled/on_demand/alert_scan)
- status (pending/running/completed/failed)
- celery_task_id — for tracking in Flower
- started_at
- completed_at
- created_at

feedback
- id (UUID)
- report_id (foreign key → reports)
- user_id (foreign key → users)
- rating (integer, 1-5)
- comment (text, optional)
- created_at

So your sub-URL discovery strategy for MVP — in priority order:
Check grey.com/llms.txt — curated important pages, LLM friendly
Check grey.com/sitemap.xml via ultimate-sitemap-parser — full URL list
Check grey.com/robots.txt — see what's allowed
Fall back to fixed common paths — /pricing, /features, /blog, /about


summary:
Serper
Returns URL, title, short snippet only — metadata, no full content
Cheapest option — $0.30-$1 per 1,000 queries
Google search results only
Risk: Google sued SerpAPI in December 2025 — legal spillover risk to Serper
Role in your platform: Fallback when Tavily fails
Tavily
Built specifically for LLM agents — best in class for your use case
Four endpoints:
/search — finds relevant URLs + snippets
/extract — takes URLs, returns clean markdown (up to 20 URLs per call)
/crawl — maps site + extracts content
/map — discovers all URLs on a domain
Returns clean markdown directly — no HTML cleaning needed
Native LangChain integration
Role in your platform: Primary search + extraction tool
BeautifulSoup + Playwright
Free but returns raw HTML — requires manual cleaning
Playwright needed for JS-rendered pages
Too much extra work for MVP
Decision: Document it but use Tavily for MVP instead
Firecrawl
Open source, self-hostable
Similar to Tavily — returns clean LLM-ready markdown
Best in class for full site crawling
/map endpoint cleaner than parsing sitemap.xml manually
Free tier: 500 credits. Paid from $16/month
Hidden cost: JSON extraction + Enhanced Mode = 9 credits per page not 1
Role in your platform: Post-MVP consideration for deep site crawling
Decision for MVP:
Tavily for everything — search, extract, map
Serper as fallback
BeautifulSoup noted in docs but not built for MVP
Firecrawl revisit post-MVP for full site crawling

Now your complete final API endpoint list:
Auth:
POST /auth/google
POST /auth/logout
Competitors:
GET /competitors
POST /competitors
GET /competitors/{id}
PATCH /competitors/{id}
DELETE /competitors/{id}
Profile:
GET /profile
PATCH /profile
Reports:
GET /reports
GET /reports/{id}
Alerts:
GET /alerts
GET /alerts/{id}
Research:
POST /research/trigger
Schedule:
GET /schedule
PATCH /schedule
Admin:
GET /admin/logs
Feedback:
POST /reports/{id}/feedback
GET /reports/{id}/feedback


Section 11 complete. Three things:
Transparency, control, speed as UX principles
Star rating on every report
Rating tracked in Prometheus, alert if drops below 3 stars


Viewed database.py:8-44
Edited database.py

Here's the full before/after when you make the switch to Alembic:

---

### Step 1 — Generate the baseline migration (run once)

```bash
# Inside the container or with your venv active
alembic revision --autogenerate -m "initial schema"
```

This reads your SQLModel models and generates a file like `alembic/versions/abc123_initial_schema.py`.

---

### Step 2 — `database.py` changes

**Now (create_all):**
```python
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

**After switching to Alembic:**
```python
from alembic import command
from alembic.config import Config

async def init_db():
    """Run pending Alembic migrations on startup."""
    alembic_cfg = Config("alembic.ini")
    
    # run_sync because alembic is synchronous
    async with async_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: command.upgrade(
                alembic_cfg.set_section_option(
                    "alembic", "sqlalchemy.url", str(sync_conn.engine.url)
                ) or command.upgrade(alembic_cfg, "head")
            )
        )
    log.info("db.migrations.applied")
```

Or the simpler, more common pattern — just call it synchronously via a subprocess/script:

```python
from alembic.config import Config
from alembic import command

def run_migrations():
    """Called synchronously before the async app starts."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

# In lifespan:
async def lifespan(app: FastAPI):
    run_migrations()   # sync call is fine here before the event loop is busy
    yield
```

---

### Step 3 — Future schema changes

```bash
# 1. Modify your SQLModel model
# 2. Generate migration
alembic revision --autogenerate -m "add company field to user"

# 3. Apply it (or let init_db() apply it automatically on next deploy)
alembic upgrade head
```

---

### Key difference in practice

| | `create_all` | Alembic |
|---|---|---|
| First run | Creates tables | Creates tables (via migration) |
| Schema change | You must `drop_all` + `create_all` or do it manually | Just `alembic upgrade head` |
| Data safety | ⚠️ Drop-recreate loses data | ✅ Incremental, data preserved |
| Best for | Early dev / prototyping | Staging + Production |

You're at the right stage to be on `create_all` — switch to Alembic once your schema starts stabilising.