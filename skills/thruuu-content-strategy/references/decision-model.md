# Decision model

How `analyze.py` turns clusters into rows, actions and priorities. Values live in `scripts/thresholds.json`; this file gives the reason for each. The guide (`content-strategy-guide.md`, section 4) uses the same rule numbers.

## Contents

1. Inputs and the business profile
2. Signals per cluster
3. Action per cluster (rules R1 to R14)
4. From clusters to rows
5. Priority score
6. AI Overview visibility and off-site actions
7. Monthly loop
8. Threshold reasons

## 1. Inputs and the business profile

The Topic Clusters project is the backbone (one cluster = one page). The AIO report is joined to it by keyword text (lower case, whitespace collapsed). The business profile is required: offer, audience, brand names, **confirmed competitors** (name, aliases, domain), whether competitor comparison pages are wanted, business value by category or keyword, and skip terms. Only confirmed competitors count as competitors anywhere in the model; Google, IBM or an integration partner named in an AI Overview do not.

## 2. Signals per cluster

- **Main-keyword position, one per row.** From the fresher source: the AIO report when it tracks your brand and its run is no more than a day older than the Topic Clusters project (it is the source that re-runs); otherwise Topic Clusters, which only gives the main keyword's position on a single-keyword cluster. The source and date are stored with the position. A Topic Clusters position more than 45 days older than the AIO run is flagged `STALE_POSITION`. When the two sources disagree on whether the main keyword ranks top 20, the row is flagged `SOURCES_DISAGREE`.
- **Target URL**: the URL ranking for the main keyword; else the URL ranking top 20 for the most cluster keywords; else Topic Clusters `bestPageUrl`. `SOURCE_CONFLICT` when the two sources name different URLs.
- **Best evidence**: the target URL's best position on any cluster keyword, with that keyword. Shown only as "page best #N", never as the main keyword's position.
- **SERP shape** (`format`): video and forum visibility from the cluster's `serpFeatures`, shown only on clusters with 3+ keywords. The cluster's Mixed SERP blends the results of all its keywords; it is not any single keyword's results page.
- **Content guidance** (`guide`), computed per cluster on a capped keyword set: the main keyword plus the highest-volume keywords with an AI Overview, `top10_per_cluster` in all (3). Two SERP views, each labelled with its source and never compared (different dates, one is a blend): the **keyword top 10** (`topOrganicResults`, the exact results page of one keyword on the AIO run date) and the **cluster Mixed SERP** (all the cluster's keywords at clustering time). Signals: list-title share in each view and a format suggestion (listicle when both are at 60%+, not a listicle when both are at 25% or less, else mixed); brands the AI Overviews name, by frequency then order, with your position on the main keyword; AI Overview `themes`; PAA, video and forum shares; the domains the AI cites. It guides the article (format, brands, themes, features) and never writes an outline, headings, title or word count: that is the thruuu brief.
- **Ranks, not cited** (`RANKS_NOT_CITED`): your page is in the top 10 for one of those keywords, the keyword has an AI Overview, and no source is on your domain. No score change: rows at 1 to 3 already get the AI Overview rules R7 to R9.
- **Page type** from the URL: `home`, `help` (help or docs subdomain, `/hc/`, `/docs/`), `archive`, `editorial` (`/blog/`, `/glossary/`, `/guide/`...), else `product`. **Slug overlap**: share of the URL's last path words found in the cluster keywords.
- **Demand**: sum of keyword volumes above the **volume floor**. The floor is the smallest volume in the project when at least 20% of clusters sit on it (10/mo here); a value at the floor means "not measured". A cluster with nothing above the floor has unknown demand.
- **AI Overview state on the main keyword only**: `named_and_cited`, `named_not_cited`, `cited_not_named`, `absent_competitors_named` (a confirmed competitor is named and not you; competitors named in the query itself do not count), `absent`, or none. Named = your brand in `brands`; cited = a source on your domain. Both are read from each AI Overview's brand list and sources, so they work whatever brand the report tracks.
- **Lost**: the main keyword lost a mention or citation since the previous run.

## 3. Action per cluster (rules R1 to R14)

First match wins.

| Rule | Condition | Action | Subtype |
|---|---|---|---|
| R1 | Hidden in thruuu, or matches a profile skip rule | SKIP | skip (reason stored) |
| R2 | Names a confirmed competitor without comparison intent (not vs, alternatives, pricing, cons...) and the profile does not want competitor-navigational pages | SKIP | about the competitor itself |
| R3 | No page of yours ranks for any keyword in the cluster | CREATE | create |
| R4 | Only a home, help, archive page, or a product page on an informational cluster, ranks, and the main keyword is not top 10 | CREATE | create_dedicated |
| R5 | The ranking page is about another topic (slug overlap below 0.34) and the main keyword is not top 10 | CREATE | create_dedicated |
| R6 | The page ranks for other cluster keywords but not the main keyword | REFRESH | expand (page best 1 to 10), expand_weak (11 to 15), expand_thin (16 or worse) |
| R7 | Main keyword 1 to 3, AI Overview names competitors and not you | REFRESH | aio_citation |
| R8 | Main keyword 1 to 3, AI Overview names you but cites others | REFRESH | win_citation |
| R9 | Main keyword 1 to 3, AI Overview cites you without naming you | REFRESH | brand_anchor |
| R10 | Main keyword 1 to 3, no AI Overview gap | MONITOR | protect |
| R11 | Main keyword 4 to 10 | REFRESH | striking |
| R12 | Main keyword 11 to 20, or 21 to 50 | REFRESH | page_two, rewrite |
| R13 | Main keyword beyond 50 | CREATE | create |
| R14 | A CREATE from R3 to R5 or R13 where the site check found a page (reviewer verdict in `review.json` `siteCheck`) | see below | see below |

**R14, site check.** thruuu sees a page only when it ranks in the top 20 for a keyword, so "no page of yours ranks" is not "no page exists". Each CREATE row's main keyword, and each supporting page with 100+/mo, is checked with a `site:<domain> <keyword>` web search, or from the sitemap when web search is not available. Scripts record candidate URLs; the reviewer decides:

| Verdict | Condition | Action | Subtype and flag |
|---|---|---|---|
| existing | Editorial page on the same topic and intent | REFRESH that URL | `existing_unranked`, `FOUND_BY_SITE_SEARCH` or `FOUND_IN_SITEMAP`; position "outside thruuu's top 20" |
| owner | Only a help, tag, pricing, home or informational product page (also forced when an `existing` URL is one of these) | CREATE | `create_dedicated` with that page as `existingWeakPage`, `OWNER_PAGE_FOUND` |
| related | Same subject, different intent | CREATE | unchanged, `RELATED_PAGE_FOUND` (link the pages) |
| none | Nothing relevant | CREATE | unchanged |

The URL must be one the script recorded for that cluster. The converted cluster then goes through section 4 like any refresh: grouped by URL, so two rows finding one page, or a found page that already has a REFRESH row, become one row.

A home, help or product page that ranks top 10 is kept (R7 to R12) with `WEAK_PAGE_TYPE`, and its row goes to the **route-to-owner** list: a new article would compete with a page Google already likes, and the content team does not own it.

## 4. From clusters to rows

1. **Competitor pages.** Clusters naming a confirmed competitor with comparison intent, or naming two competitors, form one row per competitor (a two-competitor query joins the competitor with more queries). The row refreshes your best existing comparison page, else creates one.
2. **Existing pages.** REFRESH and MONITOR clusters are grouped by target URL: one row per URL, primary = the highest-demand cluster that needs work. MONITOR clusters are listed as "protect"; a URL with only MONITOR clusters goes to the protect list. When two of your editorial URLs rank top 20 in one cluster and the other URL has no row of its own, the row becomes **CONSOLIDATE** (merge the other URL into the target).
3. **New pages.** A small CREATE cluster (unknown demand or under 100/mo) folds into a REFRESH row of the same category as a section when it shares a distinctive term with that row's main keyword or is question-shaped. Head-shaped keywords (3 words or fewer, not a question) are never folded into an unrelated page.
4. Remaining CREATE clusters form **one hub row per category**: the highest-demand cluster is the hub; clusters that share a distinctive term with it, and small question-shaped clusters, become its sections; other clusters with demand become **supporting pages** listed under the hub (plan them after it), not merged into it.
5. A small question-shaped hub with no demand that shares a distinctive term with a row that has demand, in any category, folds into that row.
6. Uncategorised clusters get a row only with 100+/mo measured demand; the rest are parked.

A distinctive term is a word used by at most 10% of the project's main keywords ("marketing" and "automation" are not distinctive here; "roi" is).

## 5. Priority score

`score = demand x opportunity x competition x AIO x (business value / 2)`, computed on the row's **head clusters** (its clusters with 100+/mo measured demand; the primary if none). Folded 10/mo questions never move the score.

| Factor | Values |
|---|---|
| Demand (measured volume of the row) | 5,000+ = 5; 1,000+ = 4; 200+ = 3; 50+ = 2; else 1. **Unknown: 3 (neutral).** |
| Opportunity | striking 5; page two 4; AIO citation 4; win citation 3.5; brand anchor 3; rewrite 3; expand 3 / 2.5 / 2; existing unranked 2.5; create dedicated 2.5; create 2 |
| Competition | 1 minus 0.01 per PageRank point the cluster average is above yours, floor 0.6 (label Low at or below yours, Moderate within +10, High above) |
| AIO (main keyword of head clusters) | lost 1.5; competitors named, not you 1.3; named not cited 1.15; cited not named 1.15; else 1.0 |
| Business value | profile, 1 to 3; competitor pages use `conquest.businessValue` |

**P1**: score 12+ and 1,000+/mo measured. **P2**: score 5.5+ and 200+/mo measured, or score 5.5+ with unknown demand. **P3**: the rest. Caps: rows with unknown demand, `SOURCES_DISAGREE` or `STALE_POSITION` cannot be P1 (they say why). A `review.json` override can move a tier with a written reason. Ties break on lower effort, then demand. Every row carries `scoreBreakdown`.

The report shows at most 5 P1 and 10 P2 rows with measured demand, plus up to 5 unknown-demand P2 rows in their own table; `plan.csv` has every row.

## 6. AI Overview visibility and off-site actions

- **Share of voice**: for you and each confirmed competitor, the number and share of AI Overview keywords that name the brand and that cite its domain, with change against the previous run.
- **Who the AI cites**: top 15 cited domains, typed as own, competitor, video, community, review site or third-party, with how many AI Overviews cite them where you are not cited.
- **Off-site actions**: video, community, review and third-party domains cited on 3+ keywords where you are not cited, each with a fixed action (video, community answers, review profile, pitch inclusion). Kept apart from the article plan.

## 7. Monthly loop

- Row keys are stable: `url:` for existing pages, `cluster:<hub id>` for new pages, `competitor:<name>`. Rows are matched to the previous run by key, then by a shared primary cluster (this is how a new page that starts ranking keeps its ledger status), then by main keyword.
- Each row stores a success check: main keyword in the top 3 (from striking distance) or top 10 (other refreshes) within 8 weeks, top 20 within 8 weeks for a page found by the site check, a new page in the top 20 within 12 weeks, plus a mention or citation on the head AI Overview when there is a gap. Next run: **met** (needs real improvement over the baseline, and a different URL for a new page), **partly met** (rank met, AI Overview not yet), **regressed** (3+ places worse), or **not yet**.
- A row that moved from CREATE to REFRESH because of the site check is reported as a correction, never as a new page that now ranks.
- Site checks are cached per keyword and domain in `snapshot/site_check.json`, dated; `site_check.py queries --previous` reuses checks under 30 days old.
- `changes.md` order: wins, success checks, metrics and competitor movement, lost AI Overview entries, moved rows (a change of main keyword is reported as such, not as a ranking loss), new rows, rows that left and why (skip rule, review, now protected, or gone from the data), ledger. Ledger entries not seen this run are marked stale, never deleted.

## 8. Threshold reasons

| Threshold | Value | Why |
|---|---|---|
| `min_article_volume` | 100/mo | Below this a standalone page rarely repays a brief. |
| `volume_floor_min_share` | 20% | A single value shared by a fifth of clusters is a data floor, not a measurement. |
| Demand unknown = 3 | | Neutral: unmeasured demand neither buries nor boosts a row. It cannot reach P1 until sized. |
| Protect band | 1 to 3 | Top 3 holds most clicks; work there only for an AI Overview gap. |
| Striking band | 4 to 10 | A refresh moves pages here in weeks (industry ranges 4 to 20). |
| Page two / rewrite | 11 to 20 / 21 to 50 | Close enough that a refresh beats a new URL / relevance worth keeping. |
| `expand_mid_max` | 15 | A page at 16 to 20 on a side keyword is thin evidence; it scores like a new page. |
| `rank_top` | 20 | "Ranking" means top 20 for coverage, disagreement and cannibalisation checks. |
| `stale_tc_days` | 45 | Past a month and a half, a frozen Topic Clusters position can hide a drop. |
| `off_topic_overlap` | 0.34 | At most one in three slug words match the cluster: the page is about something else. |
| `distinctive_df_max` | 10% | Words in more than a tenth of main keywords describe the whole project, not a topic. |
| Competition slope | 0.01 per PR point, floor 0.6 | Continuous, so creates are ordered by how much stronger the SERP is, not tied in three buckets. |
| AIO modifier 1.3 | | Cited brands get about twice the organic CTR on AI Overview queries ([Seer Interactive, 2026](https://www.seerinteractive.com/insights/aio-impact-on-google-ctr-2026-update)). |
| Lost 1.5 | | A lost mention or citation is the freshest evidence of decay. |
| P1 1,000+/mo, P2 200+/mo | | Keeps a 50/mo page from outranking a 4,000/mo gap on a client's list. |
| Report caps 5 / 10 | | A plan a team can act on this quarter; the rest stays in the CSV. |
| `format.min_serps` | 3 | "Video on 100% of SERPs" on a one-keyword cluster is one SERP; notes need 3+. |
| `top10_per_cluster` | 3 | The main keyword plus two AI Overview keywords shows the results page the article must win without pulling every keyword's top 10 on a 100-keyword cluster. The pull is one paginated pass that keeps only these (3 calls on 403 keywords). |
| `guide.listicle_share` / `not_listicle_share` | 0.6 / 0.25 | A format call needs most of both views to agree; anything between is left to intent and the brief. |
| `offsite_min_keywords` | 3 | One citation is noise; three is a pattern worth an outreach task. |
| `existing_unranked` opportunity | 2.5 | Above a new page (the URL keeps its links and history) but below a page that ranks, because nothing proves Google likes it yet. |
| `site_check.max_age_days` | 30 | Matches the monthly run: each plan re-checks once, a rerun inside the month reuses the check. |
| `site_check.existing_target_pos` | 20 | The page starts outside the top 20; entering it in 8 weeks shows the refresh worked. |
| `sitemap_min_distinctive` / `_recall_with_distinctive` | 0.5 / 0.34 | Slugs are matched on the row's distinctive words, not on words every URL shares ("marketing automation"): half of them, and a third of all words. Competitor aliases count (Pardot for Salesforce). |
| `sitemap_min_recall` / `_precision` | 0.6 / 0.5 | Rows with no distinctive word need most of their words in a slug that is mostly about them. |
