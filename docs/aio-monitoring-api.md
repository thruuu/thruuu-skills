# AI Overview Monitoring API

Pull your AIO/GEO monitoring data programmatically: keyword coverage, visibility score, brand and
domain mentions, AI Overview citation rate, and the full run history behind them.

Read-only. Everything this API returns is data an AIO Monitoring report has already produced. The
API never triggers a run or spends credits.

**Requires a Professional or Agency plan.**

---

## Authentication

Every request needs your API key in the `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

Find your key in the app under **Settings → API**. Keys do not expire, and you can revoke one at
any time from the same screen.

Do not use the token from your browser session. It expires after 12 hours and cannot be revoked
individually.

**Base URL:** `{BASE_URL}`

---

## Rate limit

100 requests per 10 seconds. Over the limit you get `429` with:

```json
{ "error": "Too many attempts, please try again shortly." }
```

Standard `RateLimit-*` headers are returned on every response.

---

## Concepts

A **report** is a monitored set of keywords for one brand and domain. It is either `oneshot` (runs
once) or `scheduled` (runs daily, weekly, biweekly or monthly).

A **run** is one execution of that report: the snapshot the whole API is organised around. A
scheduled report accumulates one run per cycle, and comparing runs is how you measure movement.
Runs are identified by `resultId`.

**Only completed runs are ever returned.** A run that failed or is still in progress is excluded
everywhere, so a number you receive is always a number you can publish.

---

## Endpoints

| | |
|---|---|
| `GET /api/v2/aio-reports` | your reports |
| `GET /api/v2/aio-reports/{id}` | one report, with run history and full statistics |
| `GET /api/v2/aio-reports/{id}/runs` | run ids only, lightweight |
| `GET /api/v2/aio-reports/{id}/keywords` | keyword detail for the most recent run |
| `GET /api/v2/aio-reports/{id}/runs/{resultId}/keywords` | keyword detail for a specific run |

---

## 1. List reports

```
GET /api/v2/aio-reports
```

| Parameter | Default | Notes |
|---|---|---|
| `page` | 1 | |
| `itemsPerPage` | 10 | Maximum 100. A higher value is reduced to 100 rather than rejected. |
| `workspace_id` | none | Restrict to one workspace. |

An API key sees every report its account can see in the app, including reports owned by teammates
on a company account.

```json
{
  "items": [
    {
      "id": "6aae62f8e1574c2167a51750",
      "label": "test member",
      "brandName": "thruuu",
      "domain": "thruuu.com",
      "subPath": null,
      "type": "oneshot",
      "status": "done",
      "schedule": { "frequency": null, "nextRunAt": null },
      "searchParam": {
        "location": null, "country": "US", "language": "en",
        "search_engine": "google.com", "device": "desktop", "domain": null
      },
      "latestResultId": "6aae62ffb2bcceabef82de1e",
      "resultsTotal": 1,
      "createdAt": "2026-09-19T10:24:56.370Z"
    }
  ],
  "total": 28,
  "page": 1,
  "itemsPerPage": 1
}
```

`resultsTotal` is how many completed runs the report has. `searchParam` is the search configuration
the report runs under (location, language, device).

---

## 2. Get a report, with statistics

```
GET /api/v2/aio-reports/{id}
```

Returns the report plus its completed runs, each carrying a full statistics block. This is the
endpoint your reporting is built on.

| Parameter | Default | Notes |
|---|---|---|
| `runs` | none | Return the N most recent completed runs. **Takes precedence over `days`.** Maximum 365. |
| `days` | 30 | Return runs from the last N days, or `all` for the full history. Capped at 365 runs. |
| `topN` | 10 | How many entries to return in each of the three "most mentioned" tables. Maximum 100. |

**Use `runs` when you want a fixed number of snapshots**: `?runs=2` gives you this run and the
previous one, which is what a period-over-period comparison needs, and it does not depend on knowing
the report's schedule. `days` is a time window, so on a monthly report `days=30` may return a single
run, and on a daily report it returns thirty.

Size matters here. On a 204-run report, `?runs=2` is about 5 KB and `?days=all` is about 500 KB.

```json
{
  "report": {
    "id": "69a3fe86f59fb8928fb40a5c",
    "label": "Marketing Automation (Example)",
    "brandName": "HubSpot",
    "domain": "hubspot.com",
    "subPath": null,
    "type": "scheduled",
    "status": "running",
    "schedule": { "frequency": "daily", "nextRunAt": "2026-09-23T01:15:00.000Z" },
    "searchParam": { "location": null, "country": "US", "language": "en",
                     "search_engine": "google.com", "device": "desktop", "domain": null },
    "latestResultId": "6ab1d6a1144864963c9112d9",
    "resultsTotal": 204,
    "createdAt": "2026-03-01T08:53:26.172Z"
  },
  "runs": [
    {
      "resultId": "6ab1d6a1144864963c9112d9",
      "status": "done",
      "date": "2026-09-22T01:15:13.937Z",
      "stats": {
        "totalKeywords": 227,
        "aioKeywordCount": 213,
        "aioPresence": 94,
        "visibilityScore": 42,
        "brandPosition": { "avg": 2, "count": 89 },
        "aioSourceRank": { "avg": 3, "count": 52 },
        "domainCitation": { "domain": "hubspot.com", "count": 52, "share": 24, "avgPosition": 4 },
        "mostMentionedBrands": [
          { "rank": 1, "name": "hubspot", "count": 89, "share": 42, "isOwnBrand": true,  "avgPosition": 2 },
          { "rank": 2, "name": "salesforce", "count": 42, "share": 20, "isOwnBrand": false, "avgPosition": 2 },
          { "rank": 3, "name": "activecampaign", "count": 39, "share": 18, "isOwnBrand": false, "avgPosition": 4 }
        ],
        "mostMentionedDomainsAIO": [
          { "domain": "hubspot.com", "count": 52, "share": 24, "avgPosition": 4 }
        ],
        "mostMentionedDomainsInSERP": [
          { "domain": "hubspot.com", "count": 132, "avg": 7, "topTenPct": 41 }
        ],
        "organicRank": { "domain": "hubspot.com", "count": 132, "avg": 7, "topTenPct": 41 }
      }
    }
  ]
}
```

### The statistics block

| Field | Meaning |
|---|---|
| `totalKeywords` | Keywords in the report. |
| `aioKeywordCount` | How many of them returned an AI Overview. |
| `aioPresence` | `aioKeywordCount / totalKeywords`, as a percentage. How often an AI Overview appears at all. |
| `visibilityScore` | Percentage of AI-Overview keywords where your brand is mentioned. Unweighted by position or search volume: `brandPosition.count / aioKeywordCount`. Range 0-100. |
| `brandPosition` | `{ avg, count }`: where your brand is named **inside the AI Overview text**, averaged. This is not a Google ranking. `count` is how many keywords mention you. |
| `aioSourceRank` | `{ avg, count }`: your domain's average position among the AI Overview's cited sources, and how many keywords cite you. |
| `domainCitation` | Your domain's row from `mostMentionedDomainsAIO`, or `null` if you were not cited. This is your AI Overview citation rate. |
| `mostMentionedBrands` | Brands named in the AI Overview text, ranked. `share` is the percentage of AI-Overview keywords naming that brand; `isOwnBrand` flags yours. |
| `mostMentionedDomainsAIO` | Domains cited as sources, ranked by how many keywords cite them. |
| `mostMentionedDomainsInSERP` | Domains ranking organically. `avg` is average position, `topTenPct` the percentage of keywords where they place in the top ten. |
| `organicRank` | Your own domain's row from `mostMentionedDomainsInSERP`, or `null`. |

The three "most mentioned" tables are truncated to `topN` entries each.

---

## 3. List runs

```
GET /api/v2/aio-reports/{id}/runs
```

The same runs as endpoint 2, without the statistics. Use it when you need run ids and dates (to
pick a run, or to see what is available) without transferring the full history.

On a 204-run report this is about 18 KB against roughly 500 KB for the same runs from endpoint 2.

Accepts `runs` and `days`, with the same meaning as endpoint 2.

```json
{
  "report": { "resultsTotal": 204 },
  "runs": [
    { "resultId": "6ab1d6a1144864963c9112d9", "status": "done", "date": "2026-09-22T01:15:13.937Z" },
    { "resultId": "6ab085259e2b4eaaec74d6c0", "status": "done", "date": "2026-09-21T01:15:17.638Z" },
    { "resultId": "6aaf33a2dedca24f171606d4", "status": "done", "date": "2026-09-20T01:15:14.945Z" }
  ]
}
```

`report.resultsTotal` is the report's lifetime count of completed runs, not the number returned by
this request. There is no pagination here; use `runs` or `days` to bound the response.

---

## 4. Keyword detail

```
GET /api/v2/aio-reports/{id}/keywords                      # most recent completed run
GET /api/v2/aio-reports/{id}/runs/{resultId}/keywords      # a specific run
```

Per-keyword results for one run: whether an AI Overview appeared, which brands it named, which
themes it covered, where you placed, and how you rank organically. Both endpoints return the same
row shape and accept the same parameters.

| Parameter | Default | Notes |
|---|---|---|
| `page` | 1 | |
| `itemsPerPage` | 50 | Maximum 200. A higher value is reduced to 200 rather than rejected. |
| `include` | none | Comma-separated list of heavy fields to add to each row: `aiOverview`, `topOrganicResults`, or both. See below. |

```json
{
  "run": { "resultId": "6ab3f0c2d4e5a6b7c8d9e0f1", "status": "done", "date": "2026-09-22T01:15:13.937Z" },
  "keywords": [
    {
      "keyword": "what is marketing automation",
      "volume": 5400,
      "hasAIO": true,
      "brandPosition": 2,
      "brands": ["Relaymark", "Acme Flow", "Funnelly"],
      "themes": ["Definition", "Key features", "Benefits for small teams", "Common tools"],
      "ownDomainAioSource": {
        "position": 3,
        "url": "https://www.acmeflow.com/guides/marketing-automation",
        "title": "Marketing Automation Explained | Acme Flow",
        "description": "Marketing automation uses software to run repetitive campaigns for you..."
      },
      "ownDomainOrganicResult": {
        "position": 4,
        "url": "https://www.acmeflow.com/guides/marketing-automation",
        "title": "Marketing Automation Explained"
      },
      "aioSERPOverlapCount": 3
    }
  ],
  "total": 227,
  "page": 1,
  "itemsPerPage": 1
}
```

| Field | Meaning |
|---|---|
| `keyword` | The search term. |
| `volume` | Monthly search volume, or `null` if unavailable. |
| `hasAIO` | Whether an AI Overview appeared for this keyword. |
| `brandPosition` | Where your brand is named inside the AI Overview text, or `null` if not mentioned. |
| `brands` | Every brand named in that AI Overview, in order of appearance. |
| `themes` | The subtopics the AI Overview covers, as an array of strings. Always returned; `[]` when there is no AI Overview. |
| `ownDomainAioSource` | **Your domain's** best placement among the cited sources, or `null`. Not the top source overall. |
| `ownDomainOrganicResult` | **Your domain's** best organic result, or `null`. |
| `aioSERPOverlapCount` | How many cited sources also appear in the organic results for that keyword. |

### `include`: adding heavy fields

`include` takes one value or a comma-separated list:

```
GET /api/v2/aio-reports/{id}/keywords?include=aiOverview
GET /api/v2/aio-reports/{id}/keywords?include=topOrganicResults
GET /api/v2/aio-reports/{id}/keywords?include=aiOverview,topOrganicResults
```

Spaces around values and repeated values are ignored. Pass a single comma-separated value: repeating
the parameter (`?include=aiOverview&include=topOrganicResults`) is rejected with a `400`.

Both fields are excluded by default because they are large. Each adds roughly 1.7 KB per keyword,
so on a 200-keyword page either one adds about 330 KB, and both together about 650 KB. Request them
only when you need them.

### `include=aiOverview`

Adds the AI Overview itself: its text and every cited source.

```json
"aiOverview": {
  "content": [
    { "type": "paragraph", "text": "Marketing automation uses software to run repetitive marketing tasks..." }
  ],
  "sources": [
    {
      "position": 1,
      "url": "https://www.relaymark.io/blog/marketing-automation",
      "title": "What Is Marketing Automation? A Beginner's Guide",
      "description": "Marketing automation is the practice of using software to...",
      "domain": "relaymark.io",
      "organic_position": 2
    }
  ]
}
```

Rows where `hasAIO` is false return `"aiOverview": null`.

### `include=topOrganicResults`

Adds the top 10 of the search results page for the keyword, in ranking order.

```json
"topOrganicResults": [
  {
    "position": 1,
    "title": "Marketing Automation: The Complete Guide",
    "url": "https://www.funnelly.com/marketing-automation",
    "domain": "funnelly.com",
    "serp_type": "page",
    "aio_position": null
  },
  {
    "position": 2,
    "title": "What Is Marketing Automation? A Beginner's Guide",
    "url": "https://www.relaymark.io/blog/marketing-automation",
    "domain": "relaymark.io",
    "serp_type": "page",
    "aio_position": 1
  }
]
```

| Field | Meaning |
|---|---|
| `position` | Organic ranking position. |
| `title` | Page title as shown in the results. |
| `url` | The ranking URL. |
| `domain` | The URL's domain. |
| `serp_type` | The kind of result: `page` for a standard organic listing, or a SERP feature such as `questions`, `video`, `images` or `ai overview`. |
| `aio_position` | This result's position among the AI Overview's cited sources, or `null` when it is not cited or the keyword has no AI Overview. |

Up to 10 entries per keyword. The array is returned on every row when requested, including rows
where `hasAIO` is false.

### Getting a single keyword

There is no single-keyword endpoint. To get one keyword, page through `/keywords` (up to 200 rows a
page) and match on the `keyword` field.

---

## Errors

| Status | When |
|---|---|
| `400` | A malformed id, an unrecognised query parameter, or an invalid `include` value (see below). |
| `401` | Missing or invalid API key. |
| `403` | Your plan does not include API access to AIO Monitoring. |
| `404` | The report or run does not exist, or is not yours. |
| `429` | Rate limit exceeded. |

```json
{ "message": "AI overview report not found" }
```

A report that does not exist and a report belonging to another account return the same `404`, so
report ids cannot be probed.

Run-level errors are more specific, because by then you are inside a report you own:

| Message | Meaning |
|---|---|
| `Result not found` | No such run on this report. |
| `Result not found or not yet completed` | The run exists but has not finished successfully. |
| `This report has no completed runs yet` | The report has never completed a run. |

An empty parameter value (`?days=`) is treated as if the parameter were absent.

`include` errors on the keyword endpoints:

| Message | Cause |
|---|---|
| `"include" must only contain: aiOverview, topOrganicResults` | A value other than `aiOverview` or `topOrganicResults`. |
| `"include" must be a string` | The parameter was repeated. Pass one comma-separated value instead. |

---

## A biweekly report, end to end

Two calls per report.

**1. Fetch the last two runs.**

```
GET /api/v2/aio-reports/{id}?runs=2
```

`runs[0]` is now, `runs[1]` is your previous period. Every headline number is a subtraction:

```
visibility     runs[0].stats.visibilityScore  −  runs[1].stats.visibilityScore
AIO presence   runs[0].stats.aioPresence      −  runs[1].stats.aioPresence
citation rate  runs[0].stats.domainCitation.share  −  runs[1].stats.domainCitation.share
```

Competitors come from `mostMentionedBrands`; your own row is the one with `isOwnBrand: true`.

**2. Fetch the keywords, if you need keyword-level detail.**

```
GET /api/v2/aio-reports/{id}/keywords?itemsPerPage=200
```

Keywords where you are losing ground are those with `hasAIO: true` and `brandPosition: null`: an
AI Overview appears and you are not in it. `brands` on those rows tells you who is.

Compare the same page against the previous run to get gained and lost:

```
GET /api/v2/aio-reports/{id}/runs/{previousResultId}/keywords?itemsPerPage=200
```

### Notes for automated pulls

- **Use `runs`, not `days`.** A report whose schedule you do not control may not have run inside
  your window, and `days` would return an empty list where `runs=2` returns the last two whatever
  their dates.
- **`latestResultId` on the report is the last run *attempted*.** After a failed run it is not the
  most recent run with data. `runs[0]`, or the keywords endpoint's default, is always the newest
  completed run.
- **`domainCitation` is `null` when you were not cited**, which is different from zero citations
  being reported. Handle the null rather than assuming an object.
- **Percentages are integers.** On a report with many keywords, a domain cited a handful of times
  rounds to `0`. Use `count` when you need precision.
