# thruuu API fields used by the strategy skills

Every field below was observed in real responses. Scripts read nothing else.

## Contents

1. Topic Clusters fields
2. AIO Monitoring fields
3. Traps seen on real data
4. What the API does not give you

## 1. Topic Clusters fields

| Endpoint | Fields read | Used for |
|---|---|---|
| `GET /topic-clusters/{id}` | `id`, `label`, `status`, `domain`, `pageRank`, `searchParam.{country,language,device}`, `createdAt` | Own domain, own PageRank, market check |
| `GET /topic-clusters/{id}/clusters` | `id`, `mainKw`, `mainKwVolume`, `count`, `category`, `intent`, `averagePR`, `serpFeatures[].{feature,visibility}`, `similarity[]`, `hidden`, `isFavorite`, `scraped`, `volume`, `briefId`, `isRanking`, `avgPosition`, `bestPageUrl` | Unit of work, demand, competition, format, ranking |
| `GET /topic-clusters/{id}/domains` | `hostname`, `count`, `countSERP`, `pageRank` | Own PageRank fallback, competitor context |
| `GET .../clusters/{clusterId}` | `keywords[].{keyword,volume}`, `scraped`, `mixedSerp.result[].{position,domain,serp_title,url,date_utc}` | Cluster format evidence (list titles across the cluster, `details --mixed-serp-only`). The Mixed SERP blends all its keywords' results; not one keyword's results page |
| `GET .../clusters/{clusterId}/paa` | `paa[].{question,answer,count}` | Questions to answer |
| `GET .../clusters/{clusterId}/related-searches` | `relatedSearches[].{title,url,count}` | Fan-out topics |

`serpFeatures[].feature` values seen: `paa`, `related searches`, `aio`, `video`, `forums`, `images`.

## 2. AIO Monitoring fields

| Endpoint | Fields read | Used for |
|---|---|---|
| `GET /aio-reports/{id}/runs?runs=365` | `runs[].{resultId,date}` | Choosing "now" and the run one month earlier (`--as-of`, `--gap-days`) |
| `GET /aio-reports/{id}?runs=N&topN=100` | `report.{id,label,brandName,domain,type,schedule.frequency,searchParam}`, `runs[].{resultId,date,stats}` | Report meta; stats only when the report tracks your own brand |
| `runs[].stats` | `totalKeywords`, `aioKeywordCount`, `aioPresence`, `visibilityScore`, `brandPosition`, `aioSourceRank`, `domainCitation`, `organicRank`, `mostMentionedBrands[].{name,share,isOwnBrand}`, `mostMentionedDomainsAIO[]` | Summary |
| `GET /aio-reports/{id}/runs/{resultId}/keywords?include=aiOverview` (also `GET /aio-reports/{id}/keywords` for the latest run) | `keyword`, `volume`, `hasAIO`, `brandPosition`, `brands[]`, `themes[]`, `ownDomainAioSource.{position,url}`, `ownDomainOrganicResult.{position,url}`, `aiOverview.content[].{type,text,list[]}`, `aiOverview.sources[].{position,domain,url,title,organic_position}` | Keyword-level ranking, mentions and citations for you and each confirmed competitor, cited sources, brands named (content guidance), themes to cover |
| same, `include=aiOverview,topOrganicResults` | `topOrganicResults[].{position,title,url,domain,serp_type,aio_position}` | A keyword's exact results page: format evidence (list titles), your page in the top 10 and whether the AI cites it (`RANKS_NOT_CITED`). Pulled for a capped selection (`aio_top10_latest.json`) and by the `keyword` command |

`include` is one comma-separated value (`include=aiOverview,topOrganicResults`); repeating the parameter returns 400. `themes` is always present (`[]` without an AI Overview). `topOrganicResults` is opt-in, up to 10 entries.

**Brand-neutral fields.** `brands[]` and `aiOverview.sources[]` do not depend on which brand the report tracks. The scripts derive "named" (a brand in `brands`) and "cited" (a source on the brand's domain) from them for you and every competitor, so share of voice is computed the same way whatever report you pair. `brandPosition`, `ownDomainAioSource` and `ownDomainOrganicResult` belong to the report's tracked brand and are used only when that brand is yours.

## 3. Traps seen on real data

- **AI Overviews sit on the long tail.** On the ActiveCampaign pair, 6 of 40 keywords with measured volume had an AI Overview, against 109 of 363 keywords at the volume floor. A plan that only reads head terms misses most of the AI layer; the scripts report it per page, including the questions folded into it.
- **Freshness.** Topic Clusters is a one-off snapshot; AIO runs repeat. When both give a position for the same keyword, the fresher one wins (AIO on ties within a day), and a Topic Clusters position older than 45 days is flagged `STALE_POSITION`.
- **Keyword casing differs between reports.** The HubSpot example report stores Title Case ("How To Create A Marketing Automation Workflow"); the join lower-cases both sides.

- **`avgPosition` is not the head-term position.** On a 15-keyword cluster it read 8 while the two 4,000+/mo keywords did not rank at all; it appears to average only the keywords that rank. Use the AIO keyword row for the main keyword when it exists.
- **Keyword-level ranking lives in the AIO report.** The Topic Clusters API has no per-keyword position, but `ownDomainOrganicResult` on AIO keyword rows gives your URL and position per keyword. When both reports use the same keyword list, the join restores it.
- **The two reports can disagree on ranking.** On one real pair, 35 of 281 single-keyword clusters disagreed (12%): Topic Clusters said ranking, the AIO pull said not, or the reverse, sometimes with a different URL. They are separate SERP pulls. Treat either as evidence, keep the better position, and flag it.
- **Project `pageRank` can be 0.** Fall back to your own hostname's row in `/domains` (strip `www.`).
- **Hostnames differ in form.** The project domain may be `www.example.com` while `/domains` and AIO stats say `example.com`. Normalise before comparing.
- **Duplicate keywords by case.** AIO keywords can repeat in different casing ("eCommerce" and "ecommerce"). Deduplicate on lower case.
- **`topOrganicResults` counts SERP blocks, not only pages.** Entries with `serp_type` `ai overview`, `questions`, `video` or `discussions & forums` take positions and have no url; on the test report the AI Overview is position 1, so the top 10 holds about 8 pages. `aio_position` is the result's rank among the AI Overview sources, null when it is not cited. Scripts count only `serp_type: page` entries as results.
- **Top 10 and Mixed SERP are different things.** `topOrganicResults` is one keyword's results page on the AIO run date; a cluster's `mixedSerp` blends all its keywords' results at clustering time. Use both as evidence, labelled; never diff them.
- **`ownDomainOrganicResult` carries undocumented extras** (`organic_position`, `serp_title`, `serp_description`). Scripts use the documented `position` only.
- **Project `domainConfigured`** appears on the project object but is not documented; scripts check `domain` instead.
- **Volume floors.** Many long-tail keywords report exactly 10/mo. Treat them as "low or unknown", not as measured demand.
- **`intent` values** seen: `informational`, `commercial`, `transactional`, `navigational`, `unknown`, and `null`.
- **Categories** include `Uncategorized`. Do not bundle it into one article.

## 4. What the API does not give you

- Keyword-level ranking inside a cluster without an AIO report on the same keywords.
- Clicks, impressions, traffic trend or conversions (connect Search Console for that).
- Page content of your own URL unless the cluster is scraped (1 credit).
- Any write: creating or re-running a project, running or scheduling an AIO report. Repeat runs depend on the user doing that in the app.
