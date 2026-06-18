One prompt, less complexity, faster to build.
So your query_generator_v1.yaml prompt would look something like:
Role: You are a competitive intelligence researcher.

Given:
- Competitor name: {competitor_name}
- Report type: {report_type}
- Research objective: {objective}

Generate targeted search queries in this exact format:

<web_search_queries>
  query 1
  query 2
</web_search_queries>

<news_queries>
  query 1
</news_queries>

<social_queries>
  query 1
  query 2
</social_queries>

Rules:
- Web queries should target pricing, features, product updates
- News queries should target announcements, funding, press coverage
- Social queries should target user complaints, reviews, sentiment
- All queries must be specific, recent, and mention the competitor by name

Example output for competitor "Grey":
...
Notice how we used XML tags — prompt engineering element number 1 from our list. And we gave specific rules per query type — that's the tool documentation principle.


Source validator — simplified approach for MVP:
We said heuristics. Simple rules:
Is the domain recognisable? (TechCrunch, Reuters, Bloomberg = credible)
Is it recent? (older than 90 days = lower score)
Is it relevant? (does the page content mention the competitor name?)
Is it a duplicate? (pgvector similarity check — cosine similarity > 0.92 = discard)
No LLM needed. Just fast rule-based scoring. Each source gets a score, below threshold gets dropped.

You're right on the calculation — $2 × 100 = $200 per week.

But let's complete the full picture:

Weekly: $200  
Monthly: $200 × 4 = $800

Now add infrastructure costs we estimated earlier:

Monthly API cost: $800  
Monthly infrastructure (Railway, etc): ~$700  
Total monthly cost: ~$1,500

Divide by 100 companies:

$1,500 ÷ 100 = $15 per company per month

That's your break-even price. Charge $20-30/month and you're profitable.

But here's something we didn't stress test — the $2.00 per report cost assumption. Let's break down what makes up that $2.00:

- LLM synthesis call (Claude Sonnet) → biggest cost
- LLM evaluator call (Gemini Flash) → smaller cost
- LLM query generator call (Claude Haiku) → cheap
- LLM router call (Claude Haiku) → cheap
- Tavily API calls → per query cost
- Apify → per scrape cost

Honest answer. Let's stress test it properly.

Let me search for current API pricing.

Good. Now let's do the real math with actual numbers.

Claude Sonnet 4.6 is $3.00 input / $15.00 output per million tokens. 

Let's estimate tokens per report. A report with 15 sources, each summarised to ~500 tokens = 7,500 input tokens for synthesis. Output report ~2,000 tokens.

Synthesis call cost:
- Input: 7,500 tokens × $3/1M = $0.02
- Output: 2,000 tokens × $15/1M = $0.03
- Total synthesis: $0.05

All LLM calls per report (rough estimate):

| Call | Model | Estimated cost |
|---|---|---|
| Query generator | Haiku ($1/$5) | ~$0.001 |
| Router | Haiku | ~$0.001 |
| Source summarisation x15 | Haiku | ~$0.02 |
| Synthesis | Sonnet 4.6 | ~$0.05 |
| Evaluator | Gemini Flash ($0.30/M) | ~$0.005 |
| LLM total | | ~$0.08 |

Now add Tavily. Roughly 10-20 API calls per report at ~$0.01 each = ~$0.15

Total per report estimate: ~$0.23

That's well under $2.00. Your instinct that it might be tight was cautious but the numbers actually look good.

Also worth noting — batch processing gives 50% off and prompt caching cuts cached input by 90%. With caching on repeated competitor queries, your real cost could drop significantly below $0.23.

So $2.00 per report is actually very comfortable. You have a lot of headroom.


If a user pauses their schedule on Wednesday and you need to debug why they didn't receive their Monday report — updated_at tells you exactly when the status changed to paused. Without it you'd have no audit trail.
It's a simple field but saves a lot of debugging headaches.

Instead of hardcoding schedules in your Celery beat config file, Celery beat reads the schedules table at runtime. This means:
User pauses their schedule → update status to paused in PostgreSQL → Celery beat picks it up on next tick → stops firing that user's job
User changes from weekly to daily → update frequency in PostgreSQL → Celery beat adjusts automatically
No code deployment needed to change a user's schedule. It just works.
The library that enables this is celery-sqlalchemy-scheduler — since you're using FastAPI not Django, you'd use celery-sqlalchemy-scheduler. It reads schedule config directly from PostgreSQL.


So my reading of the assignment:
Weekly scheduled report — combined, all competitors in one report. More strategic value.
Alerts — per competitor, immediate, individual.

TODO: CREATE GOLD STANDARD WEB RESOURCES


Conduct a comprehensive competitive analysis research on grey and its competitors, and generate actionable intelligence reports.

Conduct a competitive analysis of Cleva in 2026. Identify their main competitors, compare market positioning, and analyze key differentiators.