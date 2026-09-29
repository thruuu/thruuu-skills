# How the thruuu skills work

Technical reference for developers and agents: what each skill does, which API calls it makes, how the plan is scored, and the data traps to know about. The method behind the plan is explained on the thruuu blog.

The three skills run over the thruuu REST API v2. Rule thresholds and their reasons: `skills/thruuu-content-strategy/references/decision-model.md`. API field notes: `skills/thruuu-data-pull/references/api-fields.md`. Full API references: [AI Overview monitoring](https://thruuu.com/learn/aio-monitoring-api/), [Topic Clusters](https://thruuu.com/learn/topic-clusters-api/), [Content Pipeline](https://thruuu.com/learn/content-pipeline-api/).

## The skills

| Skill | Job | Why separate |
|---|---|---|
| `thruuu-data-pull` | Key check, pairing, snapshot (any past run, month-over-month pair, capped top 10 pass), cluster details, one-keyword lookup. Holds the API client the pipeline skill reuses; GET only. | One tested place for auth, pagination, rate limits and GET only. |
| `thruuu-content-strategy` | Profile interview, join, score, site check, plan, review, report, compare, ledger. | The repeatable core, offline on the snapshot (the site check is cached in it), so reruns are reproducible. |
| `thruuu-content-pipeline` | Push rows or keywords to the Content Pipeline, status, brief digest, approve on request, collect drafts, delete unstarted or stopped items, archive collected ones. | The only skill that spends credits, so every charge sits behind one confirmation step. |

Install the three folders together (for example in `~/.claude/skills/`). They work in Claude Code; on claude.ai only if the thruuu API host is on the network allowlist; not in the Claude API skills runtime, which has no network. The site check needs the WebSearch tool; without it, the sitemap fallback needs network access to the client's site. The API key comes from `THRUUU_API_KEY` (Settings > API, Professional or Agency plan) and is never printed; `THRUUU_API_BASE` defaults to `https://api.thruuu.com`.

## Which report answers what

| Question | Topic Clusters project | AIO Monitoring report |
|---|---|---|
| What topics exist and how big are they? | Clusters, volume, intent, category | Keyword volume only |
| Do I rank, and with which URL? | Per cluster: `isRanking`, `avgPosition`, `bestPageUrl` (a one-off snapshot) | Per keyword: `ownDomainOrganicResult` (re-measured every run) |
| How strong is the competition? | `averagePR` per cluster, `/domains` with PageRank | `mostMentionedDomainsInSERP` |
| What format does Google want? | `serpFeatures` (video, forums, AIO, PAA %), the cluster's `mixedSerp` | `topOrganicResults`: one keyword's top 10 |
| What questions must the page answer? | `/paa`, `/related-searches` per cluster | AI Overview text headers |
| Does the AI name or cite me? | | `hasAIO`, `brands`, `aiOverview.sources`, `themes` |

## API calls (GET only for the plan)

| Step | Call | Why |
|---|---|---|
| Find the pair | `GET /api/v2/topic-clusters`, `GET /api/v2/aio-reports` | Match on domain and `searchParam`; skip projects with no domain |
| Project facts | `GET /topic-clusters/{id}` | Domain, PageRank, creation date (the age of its positions) |
| All clusters | `GET /topic-clusters/{id}/clusters?itemsPerPage=150`, page until `total` | The unit of work |
| Competing domains | `GET /topic-clusters/{id}/domains?itemsPerPage=100` | Own PageRank when the project's is 0 |
| Pick runs | `GET /aio-reports/{id}/runs?runs=365` | This run and the one at least 28 days earlier |
| Run stats | `GET /aio-reports/{id}?runs=N&topN=100` | Report metadata and headline stats |
| AIO per keyword | `GET /aio-reports/{id}/runs/{resultId}/keywords?itemsPerPage=200&include=aiOverview`, both runs | Positions, brands, sources, themes, movement |
| Top 10 per keyword | same, `include=topOrganicResults`, one pass on the latest run, keeping the main keyword and up to 2 AI Overview keywords per cluster (`top10_per_cluster` 3) | The exact results page of the keywords that matter |
| One keyword | same, `include=aiOverview,topOrganicResults` (one comma-separated value; a repeated `include` is a 400), paged until found | A question about a single keyword |
| Cluster Mixed SERP | `GET .../clusters/{clusterId}` (`/paa`, `/related-searches` on demand) | Format evidence for the P1 and P2 rows, at most 15 calls |
| Content Pipeline | `POST/GET /api/v2/pipeline/items...`, `GET /api/v2/briefs/{id}` | Push, status, brief, review, draft, `DELETE /pipeline/items/{id}`, `POST /pipeline/items/{id}/archive` (see the [Content Pipeline reference](https://thruuu.com/learn/content-pipeline-api/)) |

A full pull for a 300-cluster project is about 14 calls, plus up to 15 for the top rows' Mixed SERPs. On the 403-keyword example, the top 10 pass took 3 calls and kept 334 keywords (one lookup per keyword would have taken 497). Rate limit: 100 calls per 10 seconds. The skills never call `POST .../scrape`.

**AIO credit formula** (thruuu's AIO cost function, checked 2026-09-26): `ceil(keywords / 20)` per run at 2 SERP pages, `ceil(keywords / 10)` at 5 pages, `ceil(keywords / 5)` at 10 pages. A 400-keyword report at 2 pages: 20 a run, about 87 a month weekly, about 600 a month daily.

## Scoring and thresholds

`score = demand x opportunity x competition x AIO x (business value / 2)`, on the row's head clusters (100+/mo measured; never on 10/mo folded questions).

- Demand buckets: 5,000+ = 5, 1,000+ = 4, 200+ = 3, 50+ = 2, else 1; unknown = 3 (neutral).
- Opportunity: striking 5, page two 4, AIO citation 4, win citation 3.5, brand anchor 3, rewrite 3, expand 3 / 2.5 / 2, existing page found by the site check 2.5, create dedicated 2.5, create 2.
- Competition: 1 minus 0.01 per PageRank point the cluster average is above yours, floor 0.6.
- AIO modifier on the main keyword: lost 1.5, competitors named not you 1.3, named not cited 1.15, cited not named 1.15.
- P1: score 12+ and 1,000+/mo measured. P2: 5.5+ and 200+/mo, or 5.5+ with unknown demand. `SOURCES_DISAGREE` and `STALE_POSITION` rows are capped at P2.

## Files per run

| File | Content |
|---|---|
| `snapshot/` | Raw pulls, incl. `aio_top10_latest.json` and `site_check.json` (cached 30 days per keyword and domain) |
| `plan.json` | Every number: rows, `guide` signals, flags, score breakdown |
| `review.json` | The agent's judgement: headline, notes, overrides with reasons, `siteCheck` verdicts, optional `guidance` lines |
| `strategy-report.md`, `plan.csv` | The deliverable; the CSV has every row, incl. `next_step`, `aio_themes`, `content_guidance`, `site_check` |
| `site-check.md` | Row, query, method, candidate URL, verdict |
| `changes.md` | Month-over-month comparison |
| `ledger.json` (workspace) | One entry per row with status and, once pushed, the pipeline item id and draft path |

Flags in `plan.csv`: `SOURCES_DISAGREE`, `STALE_POSITION` (Topic Clusters position older than 45 days), `SOURCE_CONFLICT`, `CANNIBALISATION`, `SHARED_PAGE`, `OFF_TOPIC_PAGE`, `CHECK_SIBLING_PAGE`, `WEAK_PAGE_TYPE`, `FOUND_BY_SITE_SEARCH`, `FOUND_IN_SITEMAP`, `OWNER_PAGE_FOUND`, `RELATED_PAGE_FOUND`, `RANKS_NOT_CITED`.

## Data traps, with field names

- Cluster `avgPosition` is not the main keyword's position: it averages only the keywords that rank (a cluster read 8 while its two 4,000+/mo keywords did not rank).
- Project `pageRank` can be 0: use your own row from `/domains`. Hostnames differ in form (`www.` or not); normalise.
- `latestResultId` is the last run attempted, not the last completed; use the run list.
- `topOrganicResults` counts SERP blocks: AI Overview, PAA, video and forum blocks take positions, so a top 10 holds about 8 pages. `aio_position` is null when the page is not cited.
- `mixedSerp` blends all of a cluster's keywords at clustering time; `topOrganicResults` is one keyword on the AIO run date. Label both, never diff them.
- Pipeline drafts: use `metaTitle`, not `title` (the slug). `no_credits` and `error` items cannot be resumed through the API; `workspace_id` goes in the body on POST and in the query on GET.
