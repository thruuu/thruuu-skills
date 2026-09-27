# Content Pipeline API

Run your Content Pipeline programmatically: push a keyword into a workspace's pipeline, launch it,
follow it through SERP analysis and brief generation, approve the brief, and pull the finished AI
draft back out as JSON, Markdown or Word.

Every keyword goes through three paid steps: analysis, brief and draft. The API charges exactly what
the app charges for the same actions. `GET` requests never spend credits.

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

A **pipeline** belongs to a workspace. It is created once, in the app, from the Content Pipeline
page (on a team account, by the account admin). The API cannot create one: pushing a keyword into a
workspace with no pipeline returns `404 no_active_pipeline`.

An **item** is one keyword in the pipeline. It runs through three steps, in order:

1. **Analysis.** Google results are scraped, any AI engines you asked for are queried, and the SERP
   agent analyses the competition. Starts when you launch the item.
2. **Brief.** A content brief is generated from that analysis. Starts on its own the moment the
   analysis finishes.
3. **Draft.** A full AI draft is written from the brief. Starts only when you approve the brief.

**The brief review is a deliberate checkpoint.** An item stops at `awaiting_review` and waits until
someone approves the brief, either in the app or by calling the review endpoint. Nothing moves past
it on its own.

All three steps run in the background. The API returns immediately; you follow progress by polling
the item's `status`.

**A workspace is the scope.** An API key sees every item in the workspace, including items added by
teammates in the app. Pass `workspace_id` to target a workspace other than your default one. On
`GET` and `DELETE` requests it goes in the query string; on `POST` requests it goes in the JSON body.
Use `GET /api/v2/workspaces` to list the ones your key can reach.

**A pipeline holds at most 20 active items.** Archived items do not count; everything else does,
including finished, failed and out-of-credits items. Archive items once you have pulled their draft,
and delete the ones you no longer want, or new keywords will be refused.

### Status

Every item carries one `status`:

| `status` | Meaning | What you do |
|---|---|---|
| `not_started` | Created, never launched. | Launch it (endpoint 4). |
| `running` | Analysis or brief in progress. | Wait and poll. |
| `awaiting_review` | The brief is ready for approval. `briefId` is set. | Review it (endpoint 5). |
| `generating_draft` | The draft is being written. | Wait and poll. |
| `ready` | The draft is finished. | Fetch it (endpoint 6), then archive the item (endpoint 8). |
| `error` | A step failed. The `error` field says why. | See below. |
| `no_credits` | A step was skipped because the balance was too low. Nothing was charged for it. | See below. |

Transitions happen in this order, and only forward:

```
not_started → running → awaiting_review → generating_draft → ready
```

Any step can instead end in `error` or `no_credits`.

**`error` and `no_credits` cannot be resumed through the API.** Launch and review only accept an
item that is `not_started` or `awaiting_review`, so calling them again returns `409` or `400`. To
continue, either use **Retry** on the item in the app (free on an `error`, charged on
`no_credits`), or delete the item and push the keyword again, which starts over from analysis and is
charged again.

On our own test runs, analysis took about 3 to 7 minutes and a draft about 10 to 25 minutes. Polling
once every 30 to 60 seconds is plenty.

### Credits

| Step | Cost | Charged when |
|---|---|---|
| Analysis | **6**, plus 1 per AI engine in `include_llm`, plus 1 if `search_volume` is on | When you launch the item. Reported in the response's `creditsCharged`. |
| Brief | **5** | Automatically, in the background, the moment analysis finishes. No response reports it. |
| Draft | **15** | When you call review. |

A keyword with no AI engines and no search volume costs **26 credits** end to end. With ChatGPT
added, 27.

Before each charge the balance is checked. If it is too low, that step is not charged and the item
goes to `no_credits` instead. On launch and review the request still succeeds, and the response
says so in its `message`. For the brief, you see it only as the item's `status`.

What is refunded:

- **A failed AI engine** refunds its 1 credit automatically. The analysis carries on without it.
- **Any other failed step keeps its charge.** The item goes to `error`. Retrying it in the app is
  free, because it was already paid for.
- **Deleting or archiving an item** never refunds anything.

On a team account, credits come from the company's shared balance.

**AI engines depend on the plan.** Professional can use `chatgpt`. Agency can use `chatgpt`,
`gemini`, `perplexity` and `google_ai_mode`.

---

## Endpoints

| | |
|---|---|
| `POST /api/v2/pipeline/items` | push a keyword, and optionally launch it |
| `GET /api/v2/pipeline/items` | the workspace's items, paginated, filterable by status |
| `GET /api/v2/pipeline/items/{itemId}` | one item |
| `POST /api/v2/pipeline/items/{itemId}/launch` | start the analysis, charges the analysis |
| `POST /api/v2/pipeline/items/{itemId}/review` | approve the brief and start the draft, 15 credits |
| `GET /api/v2/pipeline/items/{itemId}/draft` | the finished draft, as JSON, Markdown or Word |
| `DELETE /api/v2/pipeline/items/{itemId}` | remove an item that has not started or has failed |
| `POST /api/v2/pipeline/items/{itemId}/archive` | archive an item whose draft is ready |

---

## The item object

Every endpoint that returns an item returns this shape.

```json
{
  "id": "6a2b41c07e9d3f0012b8e104",
  "keyword": "best trail running shoes",
  "status": "awaiting_review",
  "serpId": "6a2b42f17e9d3f0012b8e1a9",
  "briefId": "6a2b44d87e9d3f0012b8e2c3",
  "draftId": null,
  "error": null,
  "params": {
    "country": "US",
    "language": "en",
    "device": "desktop",
    "searchEngine": "google.com",
    "location": null,
    "numberOfPages": 1,
    "briefTemplateId": null,
    "outlineFormatId": null,
    "useBrandKit": true,
    "searchVolume": false,
    "includeLlm": ["chatgpt"]
  },
  "createdAt": "2026-09-24T09:12:40.118Z",
  "updatedAt": "2026-09-24T09:18:03.527Z"
}
```

| Field | Meaning |
|---|---|
| `id` | The item id, used as `{itemId}`. |
| `keyword` | The keyword, trimmed. |
| `status` | Where the item is. See [Status](#status). |
| `serpId` | The SERP analysis, once analysis has finished, else `null`. Fetch it with `GET /api/v2/serps/{serpId}`. |
| `briefId` | The brief, once it has been generated, else `null`. Fetch it with `GET /api/v2/briefs/{briefId}`. |
| `draftId` | The draft. Set as soon as draft generation **starts**, so it is already present while `status` is `generating_draft`. Wait for `ready` before fetching. |
| `error` | The failure reason when `status` is `error`, else `null`. An internal message, useful for support, not meant for display. |
| `params` | The settings the item runs with, as sent on creation (see endpoint 1), in camelCase. `briefTemplateId` and `outlineFormatId` are `null` when the default is used. |
| `createdAt` | When the item was pushed. |
| `updatedAt` | When the item last changed. Moves forward on every status change. |

---

## 1. Push a keyword

```
POST /api/v2/pipeline/items
```

Adds one keyword to the workspace's pipeline. With `"launch": true`, it also starts the analysis in
the same call.

```json
{
  "keyword": "best trail running shoes",
  "workspace_id": "6a0f18e27e9d3f0012b8d001",
  "launch": true,
  "params": {
    "country": "US",
    "language": "en",
    "device": "desktop",
    "search_engine": "google.com",
    "include_llm": ["chatgpt"]
  }
}
```

| Field | Required | Default | Notes |
|---|---|---|---|
| `keyword` | yes | | One keyword. Leading and trailing spaces are trimmed. |
| `workspace_id` | | your default workspace | The target workspace. |
| `launch` | | `false` | `true` launches the item immediately and charges the analysis. |
| `params.country` | yes | | Country code, for example `US`. |
| `params.language` | yes | | Language code, for example `en`. |
| `params.device` | yes | | `desktop` or `mobile`. |
| `params.search_engine` | yes | | Google domain, for example `google.com` or `google.co.uk`. |
| `params.location` | | `null` | A more precise location for the search. |
| `params.number_of_pages` | | `1` | Result pages to analyse. `1` or `2`. |
| `params.brief_template_id` | | default template | A brief template id, from `GET /api/v2/brief-templates`. Must belong to your account. A value that is not a valid id is treated as the default. |
| `params.outline_format_id` | | default format | An outline format id, from `GET /api/v2/brief-outline-formats`. Must belong to your account. A value that is not a valid id is treated as the default. |
| `params.use_brand_kit` | | `true` | Write the brief with the workspace's Brand Kit. Has no effect when the workspace has none. |
| `params.search_volume` | | `false` | Fetch search volume. Adds 1 credit to the analysis. |
| `params.include_llm` | | `[]` | AI engines to query: `chatgpt`, `gemini`, `perplexity`, `google_ai_mode`. Each adds 1 credit to the analysis. Limited by plan. |

Any field not listed here is rejected.

**Response `201`:**

```json
{
  "item": {
    "id": "6a2b41c07e9d3f0012b8e104",
    "keyword": "best trail running shoes",
    "status": "running",
    "serpId": null,
    "briefId": null,
    "draftId": null,
    "error": null,
    "params": { "country": "US", "language": "en", "device": "desktop", "searchEngine": "google.com", "location": null, "numberOfPages": 1, "briefTemplateId": null, "outlineFormatId": null, "useBrandKit": true, "searchVolume": false, "includeLlm": ["chatgpt"] },
    "createdAt": "2026-09-24T09:12:40.118Z",
    "updatedAt": "2026-09-24T09:12:40.391Z"
  },
  "launched": true,
  "creditsCharged": 7
}
```

| Field | Meaning |
|---|---|
| `item` | The new item. |
| `launched` | `true` when the analysis started. |
| `creditsCharged` | Credits charged by this request. The analysis cost when `launched` is `true`, otherwise `0`. |
| `message` | Only when `launch` was `true` but the item did not start. |

The three outcomes:

| Request | `item.status` | `launched` | `creditsCharged` |
|---|---|---|---|
| `launch` omitted or `false` | `not_started` | `false` | `0` |
| `launch: true`, enough credits | `running` | `true` | the analysis cost |
| `launch: true`, not enough credits | `no_credits` | `false` | `0`, plus a `message` |

**Not enough credits is not an error.** The item is still created, with status `no_credits`, and
the response is still `201`:

```json
{
  "item": { "id": "6a2b41c07e9d3f0012b8e104", "status": "no_credits", "...": "..." },
  "launched": false,
  "creditsCharged": 0,
  "message": "Insufficient credits to launch this item. Analysis requires 7 credits; your account has 3 available."
}
```

Such an item cannot be relaunched through the API. Delete it, top up, and push the keyword again.

**Full pipeline.** When the pipeline already holds 20 active items, the request is refused with
`400` and nothing is created:

```json
{
  "error": "too_many_active_items",
  "active": 20,
  "limit": 20,
  "remaining": 0,
  "submitted": 1,
  "message": "You submitted 1 keyword but only 0 slots are free (20 of 20 in use). Remove 1, or free space by deleting unprocessed items or archiving items whose draft is ready."
}
```

---

## 2. List items

```
GET /api/v2/pipeline/items
```

The workspace's items, oldest first. Archived items are never included.

| Parameter | Default | Notes |
|---|---|---|
| `workspace_id` | your default workspace | |
| `page` | 1 | |
| `itemsPerPage` | 100 | No maximum is enforced. |
| `status` | | Only items with this status. One value from [Status](#status). |

```json
{
  "items": [
    {
      "id": "6a2b41c07e9d3f0012b8e104",
      "keyword": "best trail running shoes",
      "status": "awaiting_review",
      "serpId": "6a2b42f17e9d3f0012b8e1a9",
      "briefId": "6a2b44d87e9d3f0012b8e2c3",
      "draftId": null,
      "error": null,
      "params": { "country": "US", "language": "en", "device": "desktop", "searchEngine": "google.com", "location": null, "numberOfPages": 1, "briefTemplateId": null, "outlineFormatId": null, "useBrandKit": true, "searchVolume": false, "includeLlm": ["chatgpt"] },
      "createdAt": "2026-09-24T09:12:40.118Z",
      "updatedAt": "2026-09-24T09:18:03.527Z"
    }
  ],
  "page": 1,
  "itemsPerPage": 100,
  "total": 1
}
```

`total` counts every item matching the filter, not just this page. The `status` filter is applied
before paging, so pages are always full and `total` is exact.

A workspace with no items, or no pipeline at all, returns `"items": []` and `"total": 0`, not an
error.

`?status=awaiting_review` is the quickest way to find every brief waiting for approval.

---

## 3. Get an item

```
GET /api/v2/pipeline/items/{itemId}
```

One item, in the shape described in [The item object](#the-item-object). This is the call to poll.

| Parameter | Default | Notes |
|---|---|---|
| `workspace_id` | your default workspace | The item's workspace. |

An archived item returns `404`.

---

## 4. Launch an item

```
POST /api/v2/pipeline/items/{itemId}/launch
```

Starts the analysis of an item created with `launch: false`. The same action as **Run** in the app.

| Body field | Default | Notes |
|---|---|---|
| `workspace_id` | your default workspace | The item's workspace. |

**Charges the analysis: 6 credits, plus 1 per AI engine, plus 1 for search volume.** The brief (5)
follows automatically when the analysis finishes.

**Response `200`:** the same shape as endpoint 1.

```json
{
  "item": { "id": "6a2b41c07e9d3f0012b8e104", "status": "running", "...": "..." },
  "launched": true,
  "creditsCharged": 7
}
```

With too few credits, the response is still `200`, with `launched: false`, `creditsCharged: 0`, the
item at `no_credits`, and a `message`:

```
Insufficient credits to launch this item. Analysis requires 7 credits; your account has 3 available.
```

Only a `not_started` item can be launched. Anything else returns `409`, with the analysis step's own
status and the reason:

```json
{
  "error": "not_launchable",
  "status": "no_credits",
  "message": "This item cannot be launched. This item was previously skipped for insufficient credits."
}
```

| `status` in the 409 | Reason given |
|---|---|
| `running` | `Analysis is already running.` |
| `done` | `Analysis has already completed.` |
| `error` | `Analysis previously failed.` |
| `no_credits` | `This item was previously skipped for insufficient credits.` |

---

## 5. Review a brief

```
POST /api/v2/pipeline/items/{itemId}/review
```

Approves the item's brief and starts the draft. The same action as **Mark as reviewed** in the app.
Read the brief first with `GET /api/v2/briefs/{briefId}` if you want to check it.

| Body field | Default | Notes |
|---|---|---|
| `workspace_id` | your default workspace | The item's workspace. |

**Charges the draft: 15 credits**, at the moment of the call.

**Response `200`:**

```json
{
  "item": { "id": "6a2b41c07e9d3f0012b8e104", "status": "generating_draft", "draftId": "6a2b4a137e9d3f0012b8e3f7", "...": "..." }
}
```

With too few credits, the brief is still marked reviewed but the draft does not start. The response
is still `200`, the item is at `no_credits`, and a `message` is added:

```json
{
  "item": { "id": "6a2b41c07e9d3f0012b8e104", "status": "no_credits", "...": "..." },
  "message": "Insufficient credits to generate the draft. Draft generation requires 15 credits; your account has 9 available."
}
```

Because the brief is now reviewed, calling review again returns `400 not_reviewable`. To get the
draft, top up and use **Retry** on the item in the app.

| Status | `error` | When |
|---|---|---|
| `400` | `not_reviewable` | The item is not `awaiting_review`: the brief is not ready yet, or was already reviewed. |
| `400` | `brief_deleted` | The brief was deleted in the app. Nothing is charged. |

```json
{
  "error": "not_reviewable",
  "message": "This item's brief is not awaiting review. It may not have reached the review step yet, or has already been reviewed."
}
```

---

## 6. Get the draft

```
GET /api/v2/pipeline/items/{itemId}/draft
```

The finished draft. JSON by default, or a file download.

| Parameter | Default | Notes |
|---|---|---|
| `workspace_id` | your default workspace | The item's workspace. |
| `format` | JSON | `md` for a Markdown file, `docx` for a Word file. |

**JSON response `200`:**

```json
{
  "id": "6a2b4a137e9d3f0012b8e3f7",
  "title": "best-trail-running-shoes",
  "slug": "best-trail-running-shoes",
  "metaTitle": "Best Trail Running Shoes in 2026: Tested on Real Trails",
  "metaDescription": "We compared cushioning, grip and durability across twelve trail shoes to find the best pick for every runner and terrain.",
  "content": "# Best Trail Running Shoes in 2026: Tested on Real Trails\n\nPicking a trail shoe comes down to three things...",
  "wordCount": 3480,
  "language": "en",
  "completedAt": "2026-09-24T09:41:57.204Z"
}
```

| Field | Meaning |
|---|---|
| `id` | The draft id, same as the item's `draftId`. |
| `title` | The name used for the file downloads. It is the `slug` whenever one was generated, which is almost always; otherwise `metaTitle`, otherwise the keyword. For a human-readable title, use `metaTitle`, or the H1 at the top of `content`. |
| `slug` | Suggested URL slug, or `null`. |
| `metaTitle` | Suggested SEO title, or `null`. |
| `metaDescription` | Suggested meta description, or `null`. |
| `content` | The full article in Markdown, starting with its H1. |
| `wordCount` | Words in the article. |
| `language` | The article's language. |
| `completedAt` | When the draft finished. |

**File downloads.** With `format=md` or `format=docx`, the response is the file itself, with
`Content-Disposition: attachment` and a filename of `thruuu_draft_<slug>.md` or `.docx`.

| `format` | `Content-Type` |
|---|---|
| `md` | `text/markdown; charset=utf-8` |
| `docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |

Both files open with a short header before the article: the title, then slug, meta description,
language, word count and creation date, each only when present.

```
# best-trail-running-shoes

**Slug:** best-trail-running-shoes
**Meta description:** We compared cushioning, grip and durability across twelve trail shoes...
**Language:** en
**Word count:** 3480
**Created:** 2026-09-24

---

# Best Trail Running Shoes in 2026: Tested on Real Trails
...
```

**Not ready yet.** Any item that is not `ready` returns `409`, with the item's current status:

```json
{
  "error": "draft_not_ready",
  "status": "generating_draft",
  "message": "The draft for this item is not ready yet."
}
```

When the item is waiting for review, the response names the call that moves it on:

```json
{
  "error": "draft_not_ready",
  "status": "awaiting_review",
  "message": "This item's brief is awaiting review. Call POST /api/v2/pipeline/items/:itemId/review to advance it.",
  "next": "POST /api/v2/pipeline/items/:itemId/review"
}
```

A `ready` item whose draft was deleted in the app returns `404 draft_not_found`.

**Fetch the draft before archiving.** An archived item returns `404` here too.

---

## 7. Delete an item

```
DELETE /api/v2/pipeline/items/{itemId}
```

Removes an item from the pipeline and frees its slot.

| Parameter | Default | Notes |
|---|---|---|
| `workspace_id` | your default workspace | The item's workspace. Query string. |

Only items that have not started or have stopped can be deleted:

| `status` | Deletable |
|---|---|
| `not_started`, `error`, `no_credits` | Yes |
| `running`, `awaiting_review`, `generating_draft` | No |
| `ready` | No. Archive it instead (endpoint 8). |

**Response `200`:**

```json
{ "deleted": true, "id": "6a2b41c07e9d3f0012b8e104" }
```

Refused with `400`:

```json
{
  "error": "item_not_deletable",
  "message": "This item has already run and can no longer be removed."
}
```

Deleting removes the item only. A SERP analysis, brief or draft it already produced stays in your
account. Nothing is refunded.

An item at `awaiting_review` can be neither deleted nor archived: review it, or leave it.

---

## 8. Archive an item

```
POST /api/v2/pipeline/items/{itemId}/archive
```

Archives an item whose draft is ready, freeing its slot. The same action as **Archive** in the app.

| Body field | Default | Notes |
|---|---|---|
| `workspace_id` | your default workspace | The item's workspace. |

**Response `200`:** the archived item, which still reads `"status": "ready"` in this one response.

```json
{
  "item": { "id": "6a2b41c07e9d3f0012b8e104", "status": "ready", "...": "..." }
}
```

From then on the item is gone from the API: the list leaves it out, and endpoints 3 to 8 return
`404` for it. The brief and draft themselves stay in your account, in the app.

Only a `ready` item can be archived. Anything else returns `400`:

```json
{
  "error": "not_archivable",
  "message": "This item cannot be archived yet. Only items whose draft has reached 'ready' can be archived. Use DELETE /api/v2/pipeline/items/:itemId to remove an unfinished item instead."
}
```

---

## Errors

| Status | When |
|---|---|
| `400` | Invalid request body or query, malformed id, plan not entitled, account not verified, workspace not accessible, or an action the item's state does not allow. |
| `401` | Missing or invalid API key. |
| `403` | An AI engine in `include_llm` is not included in your plan. |
| `404` | The item does not exist, is not in this workspace, is archived, or is not yours; or the workspace has no pipeline. |
| `409` | Launching an item that is not `not_started`, or fetching a draft that is not ready. |
| `429` | Rate limit exceeded. |

Errors come back as a JSON object with a `message`. Most also carry a stable `error` code, which is
what to branch on:

```json
{ "error": "item_not_found", "message": "Item not found." }
```

An item that does not exist and an item belonging to another account return the same `404`, so
item ids cannot be probed.

| Status | `error` | Message |
|---|---|---|
| `400` | | `Payload validation error`. A bad body or query field. See below. |
| `400` | | `Invalid id.` `{itemId}` is not a valid id. |
| `400` | | `You cannot use this endpoint with your current plan. Please upgrade your subscription or contact the support.` The plan does not include the Content Pipeline API. |
| `400` | | `User is not verified` (endpoint 1). Verify the account's email address first. |
| `400` | | `Invalid or unauthorized workspace`. `workspace_id` is not one of your workspaces. |
| `400` | `too_many_active_items` | The pipeline is full (endpoint 1). The body also carries `active`, `limit`, `remaining` and `submitted`. |
| `400` | `invalid_brief_template` | `Brief template not found or not accessible.` |
| `400` | `invalid_outline_format` | `Outline format not found or not accessible.` |
| `400` | `not_reviewable` | Endpoint 5. The brief is not awaiting review. |
| `400` | `brief_deleted` | `The brief for this item no longer exists.` (endpoint 5) |
| `400` | `item_not_deletable` | Endpoint 7. The item has started and has not failed. |
| `400` | `not_archivable` | Endpoint 8. The draft is not ready. |
| `401` | | `Authorization token is not supplied` or `Authorization token is not valid.` |
| `403` | `llm_plan_required` | `AI Search engines not available on your plan: gemini, perplexity`, listing the engines refused. |
| `404` | `no_active_pipeline` | `No active Content Pipeline exists in this workspace. Create one from the Content Pipeline page in the app first.` (endpoint 1) |
| `404` | `item_not_found` | `Item not found.` |
| `404` | `draft_not_found` | `Draft not found.` (endpoint 6) |
| `409` | `not_launchable` | Endpoint 4. Also carries `status`. |
| `409` | `draft_not_ready` | Endpoint 6. Also carries `status`, and `next` when the item is `awaiting_review`. |

**Validation errors** list each offending field:

```json
{
  "validationErrors": {
    "number_of_pages": "\"params.number_of_pages\" must be less than or equal to 2",
    "foo": "\"params.foo\" is not allowed"
  },
  "message": "Payload validation error"
}
```

Two cases to know:

- An unknown AI engine is reported under its position in the array, not under `include_llm`:
  `{ "1": "Unsupported LLM engine: bing" }`.
- An empty query parameter (`?page=`) is rejected, not ignored: leave the parameter out instead.

---

## A keyword to a draft, end to end

**1. Push and launch the keyword.**

```
POST /api/v2/pipeline/items
```

```json
{
  "keyword": "best trail running shoes",
  "launch": true,
  "params": { "country": "US", "language": "en", "device": "desktop", "search_engine": "google.com" }
}
```

Check `launched`. If it is `false`, read `message`: you are out of credits. Keep `item.id`. This
call charged the analysis (6 credits here).

**2. Poll until the brief is ready.**

```
GET /api/v2/pipeline/items/{itemId}
```

Every 30 to 60 seconds, until `status` is `awaiting_review`. Stop if it becomes `error` or
`no_credits`. The brief (5 credits) was charged along the way.

**3. Check the brief, if you want to.**

```
GET /api/v2/briefs/{briefId}
```

**4. Approve it.**

```
POST /api/v2/pipeline/items/{itemId}/review
```

This charges the draft (15 credits). `item.status` is now `generating_draft`.

**5. Poll until the draft is ready.**

```
GET /api/v2/pipeline/items/{itemId}
```

Until `status` is `ready`.

**6. Pull the draft.**

```
GET /api/v2/pipeline/items/{itemId}/draft
GET /api/v2/pipeline/items/{itemId}/draft?format=md
```

**7. Archive the item**, to keep room in the pipeline.

```
POST /api/v2/pipeline/items/{itemId}/archive
```

Total: 26 credits. For many keywords, push them one by one, then poll the list instead of each item:
`GET /api/v2/pipeline/items?status=awaiting_review` for briefs to approve, and `?status=ready` for
drafts to collect.

### Notes for automated runs

- **One keyword per request.** There is no batch create. Push keywords one call at a time.
- **Twenty active items per pipeline.** Archive after pulling each draft, or the pipeline fills up
  and new keywords are refused with `too_many_active_items`.
- **Pull before you archive.** An archived item returns `404` everywhere, including the draft
  endpoint. The draft is still in the app.
- **`error` and `no_credits` are dead ends here.** Neither launch nor review can resume them. Retry
  in the app, or delete and push again, which is charged again from the start.
- **Review charges immediately.** 15 credits leave the balance at the moment of the call, not when
  the draft finishes. If the draft later fails, the credits are not refunded; Retry in the app is
  free.
- **Wait for `ready`, not for `draftId`.** `draftId` is filled in as soon as generation starts.
- **Use `metaTitle`, not `title`, as the article's title.** `title` is the slug.
- **`workspace_id` goes in the body on `POST`** and in the query string on `GET` and `DELETE`. Sent
  in the wrong place, it is ignored and your default workspace is used, which usually shows up as a
  `404`.
- **Plan errors are `400` here**, not `403`, and carry no `error` code. `403` on this API only means
  an AI engine your plan does not include.
