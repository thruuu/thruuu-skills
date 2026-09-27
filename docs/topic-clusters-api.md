# Topic Clusters API

Pull your Topic Clusters data programmatically: your projects, every cluster with its keywords,
SERP features and ranking, the competing domains, the People Also Ask questions and related
searches behind each cluster, and the full SERP and page content of a scraped cluster.

Mostly read-only. Every `GET` returns data a Topic Clusters project has already produced and never
spends credits. One action writes: triggering a cluster scrape, which costs 1 credit.

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

A **project** is one Topic Clusters analysis: a keyword list, grouped into clusters for one
location, language and device. A project optionally has **your domain** configured, which is what
turns on ranking data.

A **cluster** is a group of keywords that share enough of the same Google results to be targeted by
one page. Each cluster has a main keyword, a combined **Mixed SERP** (the results that appear across
its keywords), and the People Also Ask questions and related searches collected from those
keywords.

A cluster can be **scraped**. Scraping visits every page in the cluster's Mixed SERP and extracts
its content: headings, word count, images, FAQ, schema types, body text. It costs 1 credit per
cluster and runs in the background. Until a cluster is scraped, its SERP is available but the page
content is not.

**Ranking fields only exist when your domain is configured.** On a project with no domain, the
three ranking fields on cluster rows are left out entirely, not sent as `null`.

---

## Endpoints

| | |
|---|---|
| `GET /api/v2/topic-clusters` | your projects |
| `GET /api/v2/topic-clusters/{id}` | one project |
| `GET /api/v2/topic-clusters/{id}/clusters` | the project's clusters, paginated |
| `GET /api/v2/topic-clusters/{id}/clusters/{clusterId}` | one cluster, with its full SERP and page content |
| `GET /api/v2/topic-clusters/{id}/clusters/{clusterId}/paa` | one cluster's People Also Ask questions |
| `GET /api/v2/topic-clusters/{id}/clusters/{clusterId}/related-searches` | one cluster's related searches |
| `GET /api/v2/topic-clusters/{id}/domains` | competing domains across the project, paginated |
| `POST /api/v2/topic-clusters/{id}/clusters/{clusterId}/scrape` | scrape a cluster, 1 credit |

---

## 1. List projects

```
GET /api/v2/topic-clusters
```

| Parameter | Default | Notes |
|---|---|---|
| `page` | 1 | |
| `itemsPerPage` | 10 | Maximum 100. A higher value is reduced to 100 rather than rejected. |
| `workspace_id` | | Restrict to one workspace. |

Newest project first. An API key sees every project its account can see in the app, including
projects owned by teammates on a company account.

```json
{
  "items": [
    {
      "id": "6a1f3c9e2b7d4e0012a4c581",
      "label": "Patent costs UK",
      "status": "Done",
      "domain": "example.com",
      "pageRank": 38,
      "searchParam": {
        "location": null, "country": "GB", "language": "en",
        "search_engine": "google.co.uk", "device": "desktop", "urlOverlap": 4
      },
      "clusterCount": 184,
      "keywordCount": 1250,
      "createdAt": "2026-09-12T08:41:07.512Z"
    }
  ],
  "total": 14,
  "page": 1,
  "itemsPerPage": 10
}
```

| Field | Meaning |
|---|---|
| `id` | The project id, used as `{id}` on every other endpoint. |
| `label` | The project name. |
| `status` | `Init` (not processed yet), `In Progress`, or `Done`. |
| `domain` | Your domain, or `null` if none is configured. When `null`, cluster rows carry no ranking fields. |
| `pageRank` | Your domain's PageRank on a 0 to 100 scale, or `null` when no domain is configured or no rank was computed. |
| `searchParam` | The search configuration the project was analysed under: location, country, language, search engine, device. `urlOverlap` is how many shared results two keywords need to join the same cluster, or `null` if the default was used. |
| `clusterCount` | Clusters in the project. |
| `keywordCount` | Keywords the project was created with. |
| `createdAt` | When the project was created. |

---

## 2. Get a project

```
GET /api/v2/topic-clusters/{id}
```

The same object as one row of endpoint 1, fetched by id. No parameters.

```json
{
  "id": "6a1f3c9e2b7d4e0012a4c581",
  "label": "Patent costs UK",
  "status": "Done",
  "domain": "example.com",
  "pageRank": 38,
  "searchParam": {
    "location": null, "country": "GB", "language": "en",
    "search_engine": "google.co.uk", "device": "desktop", "urlOverlap": 4
  },
  "clusterCount": 184,
  "keywordCount": 1250,
  "createdAt": "2026-09-12T08:41:07.512Z"
}
```

---

## 3. List clusters

```
GET /api/v2/topic-clusters/{id}/clusters
```

The project's clusters, as the app's cluster cards show them. Rows come back in the project's
stored cluster order, which does not change between calls, so paging through is safe.

| Parameter | Default | Notes |
|---|---|---|
| `page` | 1 | |
| `itemsPerPage` | 40 | Maximum 150. A higher value is reduced to 150 rather than rejected. |

```json
{
  "items": [
    {
      "id": "6a1f3d4b2b7d4e0012a4c5f0",
      "mainKw": "how much does a patent cost uk",
      "mainKwVolume": 880,
      "count": 12,
      "category": "Patent Costs in the UK",
      "intent": "informational",
      "averagePR": 41,
      "serpFeatures": [
        { "feature": "paa", "visibility": 100 },
        { "feature": "related searches", "visibility": 100 },
        { "feature": "aio", "visibility": 92 }
      ],
      "similarity": [
        "how much does a patent cost uk",
        "cost to file a patent uk",
        "uk patent application fee"
      ],
      "hidden": false,
      "isFavorite": false,
      "scraped": false,
      "volume": 2340,
      "briefId": null,
      "isRanking": true,
      "avgPosition": 8.4,
      "bestPageUrl": "https://example.com/patent-costs"
    }
  ],
  "total": 184,
  "page": 1,
  "itemsPerPage": 40
}
```

| Field | Meaning |
|---|---|
| `id` | The cluster id, used as `{clusterId}`. Can be `null` in the rare case the cluster record was never created; such a cluster cannot be fetched or scraped. |
| `mainKw` | The cluster's main keyword. |
| `mainKwVolume` | Monthly search volume of the main keyword alone, or `null`. |
| `count` | Number of keywords in the cluster. |
| `category` | The cluster's category, or `null` if uncategorised. |
| `intent` | Search intent, such as `informational` or `commercial`, or `null` if not classified. |
| `averagePR` | Average PageRank (0 to 100) of the domains in the cluster's SERP. A measure of how strong the competition is. |
| `serpFeatures` | SERP features present across the cluster's keywords. `visibility` is the percentage of keywords showing that feature. Features with zero visibility are left out. |
| `similarity` | Every keyword in the cluster, main keyword included. |
| `hidden` | Whether the cluster is hidden in the app. Always a boolean. |
| `isFavorite` | Whether the cluster is marked as a favourite in the app. Always a boolean. |
| `scraped` | Whether the cluster's page content has been scraped (see endpoint 8). |
| `volume` | Total monthly search volume across all the cluster's keywords, or `null`. Not the same as `mainKwVolume`. |
| `briefId` | The id of the content brief created from this cluster, or `null`. |
| `isRanking` | **Only when the project has a domain.** Whether your domain ranks for this cluster. |
| `avgPosition` | **Only when the project has a domain.** Your average organic position across the cluster's keywords, or `null`. |
| `bestPageUrl` | **Only when the project has a domain.** Your best ranking page for the cluster, or `null`. |

The three ranking fields are present or absent together, on every row, depending on the project's
`domain`. Check `domain` once on the project rather than testing each row.

---

## 4. Get a cluster

```
GET /api/v2/topic-clusters/{id}/clusters/{clusterId}
```

One cluster in full: its keywords, and its Mixed SERP with every result, People Also Ask question
and related search. Once the cluster is scraped, each SERP result also carries the page's content.
No parameters.

Size depends on whether the cluster has been scraped. Measured on real clusters: about 30 KB
unscraped, about 750 KB scraped, and up to about 2 MB for the largest. Most of a scraped response
is `body`, `kwBody` and `semanticBody`.

```json
{
  "id": "6a1f3d4b2b7d4e0012a4c5f0",
  "mainKw": "how much does a patent cost uk",
  "mainKwVolume": 880,
  "keywords": [
    { "keyword": "how much does a patent cost uk", "volume": 880 },
    { "keyword": "cost to file a patent uk", "volume": 320 }
  ],
  "intent": "informational",
  "count": 12,
  "volume": 2340,
  "category": "Patent Costs in the UK",
  "hidden": false,
  "isFavorite": false,
  "scraped": true,
  "mixedSerp": {
    "paa": [
      {
        "question": "How much does it cost to get a patent in the UK?",
        "answer": "The cost of a UK patent depends on the fees and professional help involved...",
        "source": { "link": "https://www.gov.uk/patent-your-invention", "displayed_link": "gov.uk", "title": "Patenting your invention" }
      }
    ],
    "related_searches": [
      { "title": "uk patent renewal fees", "url": "https://www.google.co.uk/search?q=uk+patent+renewal+fees" }
    ],
    "result": [
      {
        "position": 1,
        "domain": "gov.uk",
        "serp_type": "page",
        "serp_title": "Patenting your invention: What you can patent",
        "serp_description": "You can use a patent to protect your invention...",
        "url": "https://www.gov.uk/patent-your-invention",
        "type": "article",
        "canonical": "https://www.gov.uk/patent-your-invention",
        "description": "How to apply for a patent, costs and timescales.",
        "h1": "Patenting your invention",
        "h2": ["What you can patent", "How much it costs"],
        "h3": ["Filing online"],
        "published_time": { "lastUpdate": "2 years ago", "dateFormatted": "06 December 2023", "dateISO": "2023-12-06T13:44:39+01:00" },
        "ogType": "article",
        "wordCount": 1480,
        "imgCount": 3,
        "images": [{ "src": "https://www.gov.uk/images/patent.png", "alt": "Patent process" }],
        "videos": [],
        "lang": "en",
        "faq_on_page": [],
        "anchors": { "size": 42, "outboundSize": 5, "list": [{ "text": "Apply online", "href": "https://www.gov.uk/apply", "hrefDomain": "gov.uk", "rel": "", "isOutbound": false }] },
        "toc": [{ "id": 0, "level": "1", "name": "What you can patent", "tag": "h2", "children": [] }],
        "og": { "ogImage": "https://www.gov.uk/images/og.png" },
        "schema_type": ["WebPage", "BreadcrumbList"],
        "comment_questions": [],
        "body": "Patenting your invention. You can use a patent to protect your invention...",
        "kwBody": [{ "term": "patent", "tf": 49, "n": 1 }, { "term": "patent application", "tf": 12, "n": 2 }],
        "semanticBody": [{ "tag": "h1", "text": "Patenting your invention", "type": "heading", "url": null, "index": 0, "length": 24 }],
        "pageRank": 91
      }
    ]
  },
  "createdAt": "2026-09-12T08:52:13.004Z",
  "updatedAt": "2026-09-20T14:03:51.887Z"
}
```

| Field | Meaning |
|---|---|
| `id` | The cluster id, same as `{clusterId}`. |
| `mainKw` | The cluster's main keyword. |
| `mainKwVolume` | Monthly search volume of the main keyword, or `null`. |
| `keywords` | Every keyword in the cluster, as `{ keyword, volume }` objects. |
| `intent` | Search intent, such as `informational`, or `null` if not classified. |
| `count` | Number of keywords in the cluster. |
| `volume` | Total monthly search volume across the cluster's keywords, or `null`. |
| `category` | The cluster's category, or `null`. |
| `hidden` | Whether the cluster is hidden in the app. |
| `isFavorite` | Whether the cluster is a favourite in the app. |
| `scraped` | Whether page content has been scraped. Same value as `scraped` on endpoint 3. |
| `mixedSerp` | The cluster's combined SERP, described below. `null` if the cluster has none. |
| `createdAt` | When the cluster was created. |
| `updatedAt` | When the cluster last changed. A completed scrape moves this forward. |

### `mixedSerp`

| Field | Meaning |
|---|---|
| `paa` | People Also Ask questions. Each entry has `question`, and when Google supplied them `answer`, `answer_list` (a list-style answer, as `[{ text }]`), `source` (`{ link, displayed_link, title }`) and `ai_overview` (an AI Overview attached to that question, with `ai_overview_contents` and `ai_overview_sources`). |
| `related_searches` | Related searches, each `{ title, url }`. |
| `result` | The SERP results, one entry per result. |

For question counts and a lighter response, use endpoints 5 and 6 instead.

### `result[]` entries

SERP fields, present whether or not the cluster is scraped:

| Field | Meaning |
|---|---|
| `position` | Position in the Mixed SERP. |
| `date`, `date_utc` | The date Google shows next to the result, as displayed and as ISO. Only on results that show one. |
| `domain` | The result's domain. |
| `serp_type` | The kind of result, for example `page` (organic) or `featured snippet`. |
| `serp_title` | The title shown in Google. |
| `serp_description` | The snippet shown in Google. |
| `url` | The result's URL. |
| `pageRank` | The domain's PageRank, 0 to 100. |

Page content fields, **only on a scraped cluster**:

| Field | Meaning |
|---|---|
| `type` | Page type, for example `article`. |
| `canonical` | Canonical URL. |
| `description` | Meta description. |
| `h1` | The H1 heading. |
| `h2`, `h3` | Arrays of H2 and H3 headings, in page order. |
| `published_time`, `modified_time` | `{ lastUpdate, dateFormatted, dateISO }`, when the page states them. |
| `ogType` | Open Graph type. |
| `wordCount` | Words in the main content. |
| `imgCount` | Images in the main content. |
| `images` | `[{ src, alt }]`. |
| `videos` | Embedded videos, `[{ src, videoTitle, ytid }]`. |
| `lang` | Declared page language, or `null`. |
| `faq_on_page` | FAQ entries found on the page, `[{ index, question, answer }]`. |
| `anchors` | Links on the page: `{ size, outboundSize, list: [{ text, href, hrefDomain, rel, isOutbound }] }`. |
| `toc` | The heading outline as a tree: `[{ id, level, name, tag, children }]`. |
| `og` | Open Graph data, such as `ogImage`. |
| `schema_type` | Schema.org types found on the page. |
| `comment_questions` | Questions found in the page's comments. |
| `body` | The main content as plain text. |
| `kwBody` | Most frequent terms in the content: `[{ term, tf, n }]`, where `tf` is the count and `n` the number of words in the term. |
| `semanticBody` | The content as ordered blocks: `[{ tag, text, type, url, index, length }]`. |

**Absent, not `null`.** A field with no value on the stored result is left out of that entry. On an
unscraped cluster, every page content field is absent from every result, so test for the key
(`"wordCount" in result`) or use `scraped`, never `result.wordCount === null`.

---

## 5. People Also Ask questions

```
GET /api/v2/topic-clusters/{id}/clusters/{clusterId}/paa
```

The cluster's People Also Ask questions, each with how many of the cluster's keywords surfaced it.
The quickest way to see which questions matter most for a cluster. No parameters.

This data is collected when the project is created, so it is available on every cluster, scraped
or not.

```json
{
  "id": "6a1f3d4b2b7d4e0012a4c5f0",
  "mainKw": "how much does a patent cost uk",
  "paa": [
    { "question": "How much does it cost to get a patent in the UK?", "answer": "The cost of a UK patent depends on the fees and professional help involved...", "count": 9 },
    { "question": "Is it worth patenting an idea?", "answer": null, "count": 4 }
  ]
}
```

| Field | Meaning |
|---|---|
| `question` | The question. |
| `answer` | Google's answer snippet, or `null` when none was captured. |
| `count` | How many keywords in the cluster showed this question. |

Sorted by `count`, highest first. Not paginated: the full list comes back in one response. A cluster
with no questions returns `"paa": []`, not an error.

---

## 6. Related searches

```
GET /api/v2/topic-clusters/{id}/clusters/{clusterId}/related-searches
```

The cluster's related searches, each with how many of the cluster's keywords surfaced it. No
parameters. Like endpoint 5, available on every cluster, scraped or not.

```json
{
  "id": "6a1f3d4b2b7d4e0012a4c5f0",
  "mainKw": "how much does a patent cost uk",
  "relatedSearches": [
    { "title": "uk patent renewal fees", "url": "https://www.google.co.uk/search?q=uk+patent+renewal+fees", "count": 7 },
    { "title": "patent attorney cost uk", "url": null, "count": 3 }
  ]
}
```

| Field | Meaning |
|---|---|
| `title` | The related search. |
| `url` | Google's link for that search, or `null`. |
| `count` | How many keywords in the cluster showed this related search. |

Sorted by `count`, highest first. Not paginated. A cluster with none returns
`"relatedSearches": []`.

---

## 7. Competing domains

```
GET /api/v2/topic-clusters/{id}/domains
```

Every domain that appears in the project's clusters, with how often. Sorted by `count`, highest
first.

| Parameter | Default | Notes |
|---|---|---|
| `page` | 1 | |
| `itemsPerPage` | 20 | Maximum 100. A higher value is reduced to 100 rather than rejected. |

```json
{
  "items": [
    { "hostname": "gov.uk", "count": 77, "countSERP": 375, "pageRank": 91 },
    { "hostname": "legalzoom.com", "count": 48, "countSERP": 167, "pageRank": 62 }
  ],
  "total": 312,
  "page": 1,
  "itemsPerPage": 20
}
```

| Field | Meaning |
|---|---|
| `hostname` | The domain. |
| `count` | Number of clusters whose Mixed SERP includes this domain. |
| `countSERP` | Total appearances across the SERPs of all the project's keywords. |
| `pageRank` | The domain's PageRank, 0 to 100, or `null`. |

A project with no domain data returns `"items": []` and `"total": 0`.

---

## 8. Scrape a cluster

```
POST /api/v2/topic-clusters/{id}/clusters/{clusterId}/scrape
```

Scrapes the page content of every result in the cluster's Mixed SERP, the same as clicking
**Analyze** on a cluster in the app. No request body.

**Costs 1 credit, charged only when the scrape succeeds.** The request itself never charges, which
is why every response says `"charged": false`. The scrape runs in the background; if it fails, you
are not charged.

| HTTP | `status` | Meaning |
|---|---|---|
| `202` | `scraping` | The scrape has started. |
| `200` | `already_scraped` | The cluster is already scraped. Nothing happens, nothing is charged. |
| `200` | `insufficient_credits` | Not enough credits. Nothing happens. |
| `503` | `scrape_service_unavailable` | The scrape service could not be reached. Nothing was charged. |

```json
{ "status": "scraping", "charged": false }
```

```json
{
  "status": "insufficient_credits",
  "charged": false,
  "message": "Insufficient credits to scrape this cluster. This action requires 1 credit; your account has 0 available."
}
```

```json
{
  "status": "scrape_service_unavailable",
  "charged": false,
  "message": "The scrape service is temporarily unavailable. No credit was charged. Try again shortly."
}
```

**Knowing when it is done.** Poll endpoint 4 (or endpoint 3) until `scraped` is `true`. On
endpoint 4, `updatedAt` also moves forward when the scrape completes.

**Do not trigger the same cluster twice while it is running.** The `already_scraped` check only
applies once a scrape has finished. Two requests made while the first scrape is still in progress
start two scrapes, and both are charged. Trigger once, then poll.

---

## Errors

| Status | When |
|---|---|
| `400` | A malformed id, or an invalid query parameter on endpoints 1, 3 and 7. |
| `401` | Missing or invalid API key. |
| `403` | Your plan does not include API access to Topic Clusters. |
| `404` | The project or cluster does not exist, or is not yours. |
| `429` | Rate limit exceeded. |
| `503` | Endpoint 8 only: the scrape service is unavailable. |

```json
{ "message": "Topic cluster not found" }
```

A project that does not exist and a project belonging to another account return the same `404`,
so project ids cannot be probed. The same applies to clusters, including a `clusterId` that belongs
to a different project than `{id}`.

| Status | Message | Meaning |
|---|---|---|
| `400` | `Invalid id.` | `{id}` or `{clusterId}` is not a valid id. |
| `400` | `Invalid workspace_id.` | `workspace_id` is not a valid id. |
| `400` | `Payload validation error` | A bad query parameter. See below. |
| `401` | `Authorization token is not supplied` | No API key sent. |
| `401` | `Authorization token is not valid.` | The key is wrong or revoked. |
| `403` | `Topic Clusters API access requires a Professional or Agency plan.` | Plan gate. The body also carries `"error": "plan_required"`. |
| `404` | `Topic cluster not found` | No such project, or not yours. |
| `404` | `Cluster not found` | No such cluster in this project, or not yours. |

Endpoints 1, 3 and 7 validate their query string strictly. A non-integer or zero `page` or
`itemsPerPage`, or any parameter they do not accept, returns `400` with the offending parameters
listed:

```json
{
  "validationErrors": { "include": "\"include\" is not allowed" },
  "message": "Payload validation error"
}
```

An empty parameter value (`?page=`) is treated as if the parameter were absent.

---

## A content-gap pull, end to end

**1. Find the project.**

```
GET /api/v2/topic-clusters
```

Note its `id`, and whether `domain` is set: that tells you whether cluster rows will carry ranking
fields.

**2. Page through the clusters.**

```
GET /api/v2/topic-clusters/{id}/clusters?itemsPerPage=150
```

Keep requesting the next `page` until you have `total` rows. Your content gaps are the rows with
`isRanking: false`, and `volume` tells you which are worth the most. Rows with a `briefId` already
have a brief.

**3. Get the questions for a gap.**

```
GET /api/v2/topic-clusters/{id}/clusters/{clusterId}/paa
```

The top of the list, by `count`, is what the page targeting that cluster needs to answer. Free, and
available without scraping.

**4. Scrape it, if you need the competitors' content.**

```
POST /api/v2/topic-clusters/{id}/clusters/{clusterId}/scrape
```

Then poll until `scraped` is `true`:

```
GET /api/v2/topic-clusters/{id}/clusters/{clusterId}
```

Each `mixedSerp.result[]` entry now carries the ranking page's headings, word count, FAQ and body.

### Notes for automated pulls

- **Check `domain`, not each row.** The ranking fields (`isRanking`, `avgPosition`,
  `bestPageUrl`) are absent on every row when the project has no domain, and present on every row
  when it has one.
- **A cluster `id` can be `null`.** Skip those rows before calling endpoints 4 to 8 with them.
- **Absent is not `null` in `mixedSerp`.** On endpoint 4, a SERP result or PAA entry with no value
  for a field leaves the key out. Endpoints 5 and 6 are the exception: `answer` and `url` are always
  present, `null` when empty.
- **Scrape once, then poll.** A second trigger while the first is running is charged a second time.
  A 503 almost always means nothing started, but if the response was lost in transit the scrape
  may be running anyway. Wait a few minutes and check `scraped` before retrying.
- **`intent` and `category` can be `null`** on projects where classification was not run.
