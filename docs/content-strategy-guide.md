# How to build a monthly content plan from Google and AI Overview data

Every month, your content team needs one answer: which pages should we write, and which should we improve? This guide shows how to get that answer from two thruuu reports: a list of pages to create or refresh, each with a target keyword, a reason backed by Google search results and AI Overview data, and a priority. Then it shows how the same list flows into finished drafts, and how the loop repeats month after month.

Everything here can be done by hand in thruuu, and three Claude skills automate it end to end. The examples use **ActiveCampaign**, an email marketing and automation brand, as an illustrative example: the data is real, collected in September 2026, but ActiveCampaign is not a client and did not take part.

## Contents

1. What you get each month
2. The workflow at a glance
3. Step 1: Set up two reports in thruuu
4. Step 2: Tell the plan about your business
5. Step 3: Create, refresh, or leave alone
6. Step 4: From topics to a page list
7. Step 5: Put the pages in order
8. Where you stand in AI Overviews
9. What the plan looks like
10. From plan to draft: the Content Pipeline
11. Month after month
12. Good to know
13. Appendix: for developers and agents

---

## 1. What you get each month

- **A short list of pages to work on**, split into "do now" (P1), "this quarter" (P2) and a backlog (P3). Each row names the page (a new one, or an existing URL to refresh), the keyword it targets, why, and how much search demand sits behind it.
- **Pages you already have that deserve attention first.** Refreshing a page that already ranks keeps its links and history and moves in weeks; a new page takes months. The plan always checks for that option before suggesting a new URL, including pages thruuu's reports cannot see (more on that in Step 3).
- **Your visibility in Google's AI Overviews**: how often the AI names your brand and links to your site, against your competitors, and which sites it quotes instead of you.
- **Guidance for each page**: the format Google rewards for that keyword, the brands and themes the AI Overview mentions, and the search features on the page.
- **A record of what changed since last month**: wins first, then pages that moved, and the effect of what you published.

For ActiveCampaign, the first plan held 59 pages: 18 refreshes of existing URLs and 41 new pages, with 2 in "do now". The top move was a refresh: its guide to marketing automation workflows already ranked #9 for "how to create a marketing automation workflow", in a group of searches worth about 9,000 a month, close enough to the top 3 that improving the page beats writing a new one.

## 2. The workflow at a glance

1. **Two reports in thruuu.** A Topic Clusters project groups your keywords into topics, one topic per page. An AI Overview (AIO) Monitoring report tracks, for the same keywords, where you rank and what Google's AI answer says.
2. **A plan.** The two reports are joined keyword by keyword. Each topic gets a decision (create, refresh, leave alone), then a priority from demand, opportunity, competition, AI Overview gaps and business value.
3. **Briefs and drafts.** For each page you pick, thruuu builds the brief and, through its Content Pipeline, the draft. You review and approve before anything is written.
4. **Next month.** The AIO report runs again on schedule, the plan is rebuilt, and the new plan is compared with the last: what improved, what slipped, what is new.

The Topic Clusters project decides **which pages** you need. The AIO report adds **where you rank on each keyword**, **what the AI says**, and **how both change over time**. You need both.

## 3. Step 1: Set up two reports in thruuu

Do this once per website:

1. **A Topic Clusters project with your domain set.** Without the domain there is no ranking data. Grow the keyword list first with People Also Ask questions and related searches, two or three rounds.
2. **An AIO Monitoring report on the same keywords, country and device.** Upload the project's keyword list, so every keyword appears in both reports. On the ActiveCampaign example, all 403 keywords matched.
3. **Schedule the AIO report monthly.** Each run becomes the baseline for the next plan.

**What it costs.** Reading your reports costs nothing. The AIO report costs credits each time it runs: a 400-keyword report reading 2 pages of Google results is 20 credits a run, so 20 credits a month on a monthly schedule. Twelve clients of that size cost about 240 credits a month. Credit costs are set in the app; check there before quoting a client.

## 4. Step 2: Tell the plan about your business

Data can tell you what people search. Only you can say what matters to your business. Before the first plan, five questions, pre-filled from the data:

1. What do you sell, and to whom?
2. Which of the brands the AI Overviews mention are **real competitors**? On the ActiveCampaign example the AI named 25 brands, from HubSpot and Mailchimp to Google and Zapier. Only confirmed competitors count in the competitive numbers; platforms and integration partners usually do not.
3. Do you want **competitor pages** (comparisons, alternatives, pricing)?
4. Which topics bring **revenue**, and which are awareness only?
5. Which topics should **never** get a page?

Anything you did not confirm is labelled as an assumption on page one of the plan.

## 5. Step 3: Create, refresh, or leave alone

Each topic is judged on one number: your position on its main keyword, from the most recent measurement. Read the table from the top; the first line that matches decides.

| Your situation | What to do | Why |
|---|---|---|
| The topic is one you never want a page for, or a query about a competitor's own product with no comparison intent | Skip it | Not your topic, or traffic you do not want |
| None of your pages ranks for any keyword in the topic | Create a new page | Nothing to improve yet (after the site check below) |
| Only your homepage, a help article, an archive page, a product page on an informational topic, or a page about something else ranks, outside the top 10 | Create a dedicated page | That page cannot be reshaped for this topic without hurting its own job |
| The same kind of page ranks in the top 10 | Keep it, and send the work to the page's owner | Google already likes it; a new article would compete with it |
| Your page ranks for other keywords of the topic, but not the main one | Refresh that page to cover the main keyword | The page is already relevant |
| Main keyword in the top 3, and the AI Overview names competitors but not you | Refresh for the AI Overview | You win the click but lose the AI answer |
| Main keyword in the top 3, and the AI Overview names you but links to someone else | Refresh to win the link | The AI recommends you and sends the reader elsewhere |
| Main keyword in the top 3, and the AI Overview links to you without naming you | Refresh to put your name in the answer | Your page is used, your brand is not |
| Main keyword in the top 3, no AI Overview gap | Protect: watch it, no work | Changing it risks more than it gains |
| Main keyword at 4 to 10 | Refresh (striking distance) | The fastest return: a refresh moves these in weeks |
| Main keyword at 11 to 20 | Refresh (page two) | Close enough that a refresh beats a new URL |
| Main keyword at 21 to 50 | Refresh with a rewrite | The page still has relevance worth keeping |
| Main keyword beyond 50 | Create a new page | Too far to recover |
| Any "create" above, when the site check finds your existing article | Refresh that article instead | The page exists; it just ranks lower than the reports can see |

Why the AI Overview lines matter: brands cited in an AI Overview get about twice the organic click-through rate on those searches ([Seer Interactive, April 2026](https://www.seerinteractive.com/insights/aio-impact-on-google-ctr-2026-update)). Google says AI Overviews use its normal ranking systems and need no special markup ([Google Search Central](https://developers.google.com/search/docs/appearance/ai-features)), so winning them is content work: direct answers, question headings, self-contained passages, original data.

### Before writing anything new: the site check

thruuu's reports see your page only when it ranks in the top 20 for a keyword they track. An article sitting at #35 is invisible to them, and a plan built on them alone would ask a writer to create a duplicate. So before any new page is written, the plan looks for an existing article on your site, with a plain web search such as `site:activecampaign.com marketing automation roi`, or through your sitemap when web search is not available.

A result counts only when it covers the **same topic with the same intent** on an article page. Then the row changes from "create" to "refresh that URL". A help-centre, tag or pricing page does not count: the new article is still written and links to it. A page on the same subject with a different angle is linked, not replaced.

On the ActiveCampaign example this caught a "do now" row. The plan wanted a new page for "salesforce marketing automation alternatives" (a group of Salesforce comparison searches worth about 5,000 a month), because no ActiveCampaign page ranked in the top 20. A web search found `/blog/pardot-alternatives`, an existing listicle on Salesforce's own B2B automation product. The plan now refreshes that post instead of writing a second one.

## 6. Step 4: From topics to a page list

Keyword clustering is precise, so many long-tail questions end up alone: 281 of the 319 topics in the example had a single keyword. A plan of 319 pages would be unusable, so topics are grouped into pages:

- **Existing pages**: one row per URL, covering every topic it serves. When two of your articles compete for the same topic, the plan suggests merging them into one.
- **Competitor pages**: all the comparison and alternatives searches about one competitor become one page.
- **New pages**: one main page (a hub) per category. Topics that share its subject, and small questions, become sections of it; other topics with real demand are listed as supporting pages to plan after the hub.
- **Pages you do not own**: help, product and home pages that rank go to their owners, not into the editorial plan.

## 7. Step 5: Put the pages in order

Each page gets a score from five things:

- **Demand**: how many searches a month it targets.
- **Opportunity**: how quickly the work can pay off. A page at #4 to #10 comes first, then page two, then AI Overview fixes, then new pages.
- **Competition**: how strong the sites already ranking are, compared with yours.
- **AI Overview gap**: a boost when the AI names competitors and not you, or when you lost a mention since last month.
- **Business value**: from your answers in Step 2.

"Do now" needs a high score and at least 1,000 measured searches a month; "this quarter" needs a good score and at least 200. Pages whose demand could not be measured get their own short list, to size in your keyword tool before you commit. The report shows at most 5 "do now" and 10 "this quarter" pages, so the list stays something a team can finish.

## 8. Where you stand in AI Overviews

The plan shows, across every keyword where Google shows an AI Overview:

- **Share of voice**: how often the AI names you, and how often it links to your site, against each competitor. In the ActiveCampaign example (AIO report of 26 September 2026), ActiveCampaign was named in 21% of the AI Overviews and linked in 8%; HubSpot was named in 49% and linked in 27%.
- **Who the AI quotes instead of you**: the sites it links to most, sorted into competitors, videos, forums, review sites and publishers.
- **Off-site actions**: when the AI keeps quoting YouTube videos, forum threads, review sites or third-party listicles, no article on your own site will win those links. The plan lists them separately: publish videos, answer in the threads, complete your review profiles, pitch the listicle authors.

A useful finding from the example: AI Overviews appeared on only 6 of the 40 keywords with measured search volume, but on 109 of the 363 long-tail questions. The AI layer lives in the questions a page answers, which is why each page's guidance looks at the questions folded into it, not only its main keyword.

## 9. What the plan looks like

One report and one spreadsheet per month:

1. **Summary**: a headline, your coverage, your AI Overview share of voice, the number of pages by action, and the first moves.
2. **AI Overview visibility**: share of voice, who the AI quotes, and pages where the AI names you but links elsewhere.
3. **The page list**: do now, this quarter, and "demand unknown", each row with its action, target keyword, URL, current position, demand, AI Overview situation and the reason in numbers.
4. **Guidance for each page**, then competitor pages, off-site actions, pages to route to their owners, pages to protect, and what was skipped and why.

**Guidance, not a brief.** For each priority page the plan adds a few lines of evidence to steer the article. It never writes the outline, headings, title or word count: that is the brief's job, and thruuu's brief does it from the live search results. For the example's "marketing automation software for startups":

- **Format**: a list of options (listicle). 7 of the 9 results for this keyword have list titles, and so do 18 of the 20 results across the whole topic.
- **Brands to mention**: HubSpot, ActiveCampaign, Klaviyo, Brevo, Mailchimp and Adobe, the brands the AI Overviews name on these searches.
- **Themes to cover** (from the AI Overviews): marketing automation, email marketing, lead scoring, customer segmentation, inbound marketing, personalization, multi-channel communication, e-commerce marketing.
- **Search features**: People Also Ask on every search in the topic; the AI Overview quotes gumloop.com and hubspot.com.

Each row ends with its next step in thruuu: open the topic, run Cluster Analysis and create the brief there, or send the row to the Content Pipeline (next section).

## 10. From plan to draft: the Content Pipeline

The plan says which pages to write. thruuu's **Content Pipeline** writes them, inside thruuu, in three steps per keyword:

1. **Analysis.** thruuu reads the Google results for the keyword (and any AI engines you choose) and analyses the competition.
2. **Brief.** thruuu builds the content brief from that analysis, on its own, as soon as the analysis ends.
3. **Draft.** thruuu writes the full article from the brief, but only after someone approves the brief.

**How the month continues after the plan.**

1. **Send the top pages.** Pick rows by number ("push rows 1, 2 and 9") or by priority. A keyword is never sent twice, and each page keeps its link to its plan row, so you can keep saying "row 3".
2. **Wait for the briefs.** Ask for the pipeline status at any time. Analysis takes a few minutes; the brief follows by itself.
3. **Review each brief.** Read a short summary in chat (title, meta description, outline headings, key questions, main points), or open it in thruuu and edit it. The draft is written from whatever the brief says when you approve it.
4. **Approve.** "Approve row 3" starts the draft. Nothing is approved without you asking.
5. **Collect the drafts.** Each finished draft is saved as Markdown or Word next to the plan, under its SEO title. Then archive the item in thruuu to free its slot.

**What it costs, and when you are asked.**

| Step | Credits | Charged |
|---|---|---|
| Analysis | 6, plus 1 per AI engine, plus 1 for search volume | When the item is launched |
| Brief | 5 | Automatically, when the analysis ends |
| Draft | 15 | When you approve the brief |

A keyword costs 26 credits from analysis to draft with no AI engine. Before anything that spends credits, the amount is shown and nothing happens without an explicit yes. Adding a keyword without launching it costs nothing. A pipeline holds 20 active items at a time.

**What the statuses mean.**

| Status | Meaning | What you do |
|---|---|---|
| Not started | Added, not launched | Launch it when ready (charged then) |
| Running | Analysis or brief in progress | Wait |
| Awaiting review | The brief is ready | Read it, edit it in thruuu if needed, approve |
| Generating draft | The article is being written | Wait (usually 10 to 25 minutes) |
| Ready | The draft is finished | Collect it, then archive the item |
| No credits | A step was skipped because the balance was too low; nothing was charged for it | Top up, then use Retry on the item in thruuu |
| Error | A step failed | Use Retry on the item in thruuu (free) |

**Example conversation.**

> **You:** Push rows 1, 2 and 9 to the pipeline and launch them.
> **Assistant:** Rows 1 and 2 are already in the pipeline, so only row 9 ("salesforce marketing automation alternatives") is new. Launching it charges 6 credits now, then 5 for the brief automatically; the draft would be another 15 when you approve. Go ahead?
> **You:** Yes.
> **Assistant:** Row 9 is running. Row 2's brief is waiting for your review.
> **You:** Show me row 2's brief.
> **Assistant:** Title, meta description, the outline headings and the key questions, then: "You can edit it in thruuu first. Approving starts the draft for 15 credits."
> **You:** Approve row 2.
> **Assistant:** Approved. The draft is being written; I will fetch it when it is ready.

## 11. Month after month

| How often | What | Why |
|---|---|---|
| Monthly | The AIO report runs, the plan is rebuilt and compared with last month | Rankings and AI answers move every month |
| Quarterly, or when your keyword list changes | Re-cluster the Topic Clusters project in thruuu | Its positions are a snapshot; after about six weeks they go stale |
| As work ships | Mark each page planned, in progress, published or dropped | So next month's plan knows what you did |

Each month's comparison opens with **wins**: pages that reached their goal, new pages that now rank, pages that moved into the top 3, and AI Overview mentions and links gained. Then come the goals still in progress, your competitors' movement in AI Overviews, pages that moved up or down the list, new pages, and pages that left the list with the reason. Every page carries a clear goal, for example "in the top 3 within 8 weeks" for a refresh at striking distance, or "in the top 20 within 12 weeks" for a new page, so progress is measured, not guessed.

## 12. Good to know

- **"No page ranks" is not "no page exists."** The reports see the top 20 only; the site check covers the rest.
- **A topic's combined results are not one keyword's results.** thruuu's Mixed SERP blends the results of every keyword in a topic. It shows what the topic as a whole competes with; the exact results page of one keyword is a separate view. The plan uses both, labelled, and does not compare them (they are collected on different dates, and one is a blend).
- **The two reports can disagree** on whether a page ranks (on the example, 12% of single-keyword topics). They are separate measurements; the more recent one wins, and the page is capped at "this quarter" until you check Search Console.
- **Some keyword volumes are placeholders.** When a large share of keywords shows the same minimum volume (10 a month on the example), that means "not measured", not "tiny".
- **Not every brand is a competitor.** On a search like "HubSpot vs Mailchimp", the AI Overview will always name both; judge those pages on rankings.
- **No traffic data.** The reports give rankings and AI answers, not clicks or conversions. Connect Search Console for those.

---

## 13. Appendix: for developers and agents

Everything above can be run by three Claude skills over the thruuu REST API v2. This appendix holds the technical detail they rely on. Rule thresholds and their reasons: `skills/thruuu-content-strategy/references/decision-model.md`. API field notes: `skills/thruuu-data-pull/references/api-fields.md`. Full API references: `aio-monitoring-api.md`, `topic-clusters-api.md`, `content-pipeline-api.md`.

### A. The skills

| Skill | Job | Why separate |
|---|---|---|
| `thruuu-data-pull` | Key check, pairing, snapshot (any past run, month-over-month pair, capped top 10 pass), cluster details, one-keyword lookup. Holds the API client the pipeline skill reuses; GET only. | One tested place for auth, pagination, rate limits and GET only. |
| `thruuu-content-strategy` | Profile interview, join, score, site check, plan, review, report, compare, ledger. | The repeatable core, offline on the snapshot (the site check is cached in it), so reruns are reproducible. |
| `thruuu-content-pipeline` | Push rows or keywords to the Content Pipeline, status, brief digest, approve on request, collect drafts. | The only skill that spends credits, so every charge sits behind one confirmation step. |

Install the three folders together (for example in `~/.claude/skills/`). They work in Claude Code; on claude.ai only if the thruuu API host is on the network allowlist; not in the Claude API skills runtime, which has no network. The site check needs the WebSearch tool; without it, the sitemap fallback needs network access to the client's site. The API key comes from `THRUUU_API_KEY` (Settings > API, Professional or Agency plan) and is never printed; `THRUUU_API_BASE` defaults to `https://api.thruuu.com`.

### B. Which report answers what

| Question | Topic Clusters project | AIO Monitoring report |
|---|---|---|
| What topics exist and how big are they? | Clusters, volume, intent, category | Keyword volume only |
| Do I rank, and with which URL? | Per cluster: `isRanking`, `avgPosition`, `bestPageUrl` (a one-off snapshot) | Per keyword: `ownDomainOrganicResult` (re-measured every run) |
| How strong is the competition? | `averagePR` per cluster, `/domains` with PageRank | `mostMentionedDomainsInSERP` |
| What format does Google want? | `serpFeatures` (video, forums, AIO, PAA %), the cluster's `mixedSerp` | `topOrganicResults`: one keyword's top 10 |
| What questions must the page answer? | `/paa`, `/related-searches` per cluster | AI Overview text headers |
| Does the AI name or cite me? | | `hasAIO`, `brands`, `aiOverview.sources`, `themes` |

### C. API calls (GET only for the plan)

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
| Content Pipeline | `POST/GET /api/v2/pipeline/items...`, `GET /api/v2/briefs/{id}` | Push, status, brief, review, draft (see `content-pipeline-api.md`) |

A full pull for a 300-cluster project is about 14 calls, plus up to 15 for the top rows' Mixed SERPs. On the 403-keyword example, the top 10 pass took 3 calls and kept 334 keywords (one lookup per keyword would have taken 497). Rate limit: 100 calls per 10 seconds. The skills never call `POST .../scrape`.

**AIO credit formula** (thruuu's AIO cost function, checked 2026-09-26): `ceil(keywords / 20)` per run at 2 SERP pages, `ceil(keywords / 10)` at 5 pages, `ceil(keywords / 5)` at 10 pages. A 400-keyword report at 2 pages: 20 a run, about 87 a month weekly, about 600 a month daily.

### D. Scoring and thresholds

`score = demand x opportunity x competition x AIO x (business value / 2)`, on the row's head clusters (100+/mo measured; never on 10/mo folded questions).

- Demand buckets: 5,000+ = 5, 1,000+ = 4, 200+ = 3, 50+ = 2, else 1; unknown = 3 (neutral).
- Opportunity: striking 5, page two 4, AIO citation 4, win citation 3.5, brand anchor 3, rewrite 3, expand 3 / 2.5 / 2, existing page found by the site check 2.5, create dedicated 2.5, create 2.
- Competition: 1 minus 0.01 per PageRank point the cluster average is above yours, floor 0.6.
- AIO modifier on the main keyword: lost 1.5, competitors named not you 1.3, named not cited 1.15, cited not named 1.15.
- P1: score 12+ and 1,000+/mo measured. P2: 5.5+ and 200+/mo, or 5.5+ with unknown demand. `SOURCES_DISAGREE` and `STALE_POSITION` rows are capped at P2.

### E. Files per run

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

### F. Data traps, with field names

- Cluster `avgPosition` is not the main keyword's position: it averages only the keywords that rank (a cluster read 8 while its two 4,000+/mo keywords did not rank).
- Project `pageRank` can be 0: use your own row from `/domains`. Hostnames differ in form (`www.` or not); normalise.
- `latestResultId` is the last run attempted, not the last completed; use the run list.
- `topOrganicResults` counts SERP blocks: AI Overview, PAA, video and forum blocks take positions, so a top 10 holds about 8 pages. `aio_position` is null when the page is not cited.
- `mixedSerp` blends all of a cluster's keywords at clustering time; `topOrganicResults` is one keyword on the AIO run date. Label both, never diff them.
- Pipeline drafts: use `metaTitle`, not `title` (the slug). `no_credits` and `error` items cannot be resumed through the API; `workspace_id` goes in the body on POST and in the query on GET.
