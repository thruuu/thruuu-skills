#!/usr/bin/env python3
"""Render plan.json (+ review.json) into the strategy report and plan.csv.

  python3 render.py --plan plan.json [--review review.json] [--profile profile.json] [--out-dir DIR]

review.json holds the judgement layer: a headline, notes, and action or priority overrides that
each carry a reason. It is validated here and never changes a number. The report shows at most
5 P1 and 10 P2 rows; plan.csv holds every row, and the report states the same counts as the CSV.
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter

VALID_ACTIONS = {"CREATE", "REFRESH", "CONSOLIDATE", "SKIP", "MONITOR"}
VALID_PRIORITIES = {"P1", "P2", "P3"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def n(x):
    return f"{int(x):,}" if isinstance(x, (int, float)) else "unknown"


def md(s):
    return str(s if s is not None else "").replace("|", "/").replace("\n", " ")


def short_url(u, domain):
    if not u:
        return ""
    for p in ("https://", "http://", "www."):
        u = u.replace(p, "")
    return (u[len(domain):] or "/") if u.startswith(domain) else u


def aio_cell(r):
    h = r["aio"]["head"]
    comps = [c for c, _ in r["aio"]["competitors"][:3]]
    return {
        None: "no AIO on main keyword",
        "absent": "AIO names no brand",
        "absent_competitors_named": "names " + ", ".join(comps) + "; not you" if comps else "you are absent",
        "named_not_cited": "names you, cites others",
        "cited_not_named": "cites you, does not name you",
        "named_and_cited": "named and cited",
    }.get(h, h)


def pos_cell(r):
    if {"FOUND_BY_SITE_SEARCH", "FOUND_IN_SITEMAP"} & set(r["flags"]) and r["position"] is None:
        return "outside thruuu's top 20 (" + ("site search" if "FOUND_BY_SITE_SEARCH" in r["flags"] else "sitemap") + ")"
    if r["position"] is not None:
        src = " (TC)" if (r.get("posSource") or "").startswith("Topic Clusters") else ""
        return f"#{r['position']}{src}"
    be = r.get("bestEvidence") or {}
    if r["action"] in ("REFRESH", "CONSOLIDATE", "ROUTE") and be.get("position"):
        return f"not ranking (page best #{be['position']})"
    return "not ranking"


def target_cell(r, dom):
    if r["target"]:
        return short_url(r["target"], dom)
    if r.get("existingWeakPage") and "OWNER_PAGE_FOUND" in r["flags"]:
        return "new page (site has " + short_url(r["existingWeakPage"], dom) + ", owner page)"
    if r.get("existingWeakPage"):
        return "new page (only " + ("the homepage" if short_url(r["existingWeakPage"], dom) == "/" else short_url(r["existingWeakPage"], dom)) + " ranks today)"
    return "new page"


def next_step(r):
    lead = "size the demand in your keyword tool, then " if not r["demandKnown"] else ""
    return f"Next: {lead}run Cluster Analysis on the '{r['mainKw']}' cluster in thruuu, then create the brief there, or push row {r.get('rank')} to the thruuu Content Pipeline (thruuu-content-pipeline)."


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def guidance_lines(r):
    """Template phrasing of plan.json `guide`; review.json rows[key].guidance replaces it."""
    g = r.get("guide") or {}
    out = []
    f = g.get("format") or {}
    ev = []
    if f.get("keywordListicle"):
        ev.append(f"{f['keywordListicle'][0]} of {f['keywordListicle'][1]} results in the keyword top 10 have list titles")
    if f.get("mixedSerpListicle"):
        ev.append(f"{f['mixedSerpListicle'][0]} of {f['mixedSerpListicle'][1]} in the cluster Mixed SERP")
    if f.get("suggestion"):
        lead = {"listicle": "Format: a list of options (listicle)", "not_listicle": "Format: not a listicle", "mixed": "Format: no single pattern, choose by intent"}[f["suggestion"]]
        out.append(f"{lead}: {'; '.join(ev)}.")
    if g.get("brands"):
        names = ", ".join(b["brand"] + (" (you)" if b["own"] else "") for b in g["brands"])
        line = f"Brands the AI Overview names ({g['aioKeywords']} AIO {'keyword' if g['aioKeywords'] == 1 else 'keywords'}): {names}."
        on = g.get("ownNamedOnMain")
        if on and on[0]:
            line += f" You are named {ordinal(on[0])} of {on[1]} on the main keyword."
        elif on:
            line += f" You are not among the {on[1]} brands named on the main keyword."
        out.append(line)
    if g.get("themes"):
        out.append("AI Overview themes to cover: " + ", ".join(g["themes"][:8]) + ".")
    feats = [f"{'PAA' if k == 'paa' else 'AI Overview' if k == 'aio' else k} on {v}%" for k, v in (g.get("clusterFeatures") or {}).items()]
    bits = []
    if feats:
        bits.append("cluster Mixed SERP: " + ", ".join(feats) + " of SERPs")
    if g.get("keywordBlocks"):
        bits.append("keyword top 10: " + ", ".join(g["keywordBlocks"]))
    if bits:
        out.append("SERP features: " + "; ".join(bits) + ".")
    if g.get("aiCites"):
        out.append("The AI Overview cites " + ", ".join(g["aiCites"]) + " from the keyword top 10.")
    return out


def validate_review(review, keys):
    errors = []
    for k, v in (review.get("rows") or {}).items():
        if k not in keys:
            errors.append(f"review.json: unknown row key {k}")
        if v.get("action") and v["action"] not in VALID_ACTIONS:
            errors.append(f"review.json: invalid action {v['action']} on {k}")
        if v.get("priority") and v["priority"] not in VALID_PRIORITIES:
            errors.append(f"review.json: invalid priority {v['priority']} on {k}")
        gd = v.get("guidance")
        if gd is not None and (not isinstance(gd, list) or len(gd) > 5 or any(not isinstance(x, str) or len(x) > 240 for x in gd)):
            errors.append(f"review.json: guidance on {k} must be a list of at most 5 short lines")
        if (v.get("action") or v.get("priority")) and not v.get("note"):
            errors.append(f"review.json: override on {k} needs a note explaining why")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--review")
    ap.add_argument("--profile")
    ap.add_argument("--out-dir")
    a = ap.parse_args()
    plan = load(a.plan)
    out = a.out_dir or os.path.dirname(os.path.abspath(a.plan))
    review = load(a.review) if a.review and os.path.exists(a.review) else {}
    profile = load(a.profile) if a.profile and os.path.exists(a.profile) else {}
    rows, owner = plan["rows"], plan.get("ownerRows", [])
    errs = validate_review(review, {r["key"] for r in rows + owner})
    if errs:
        sys.exit("\n".join(errs))
    for r in rows + owner:
        o = (review.get("rows") or {}).get(r["key"])
        if o:
            r["reviewNote"] = o.get("note")
            r["reviewGuidance"] = o.get("guidance")
            if o.get("action") and o["action"] != r["action"]:
                r["originalAction"], r["action"] = r["action"], o["action"]
            if o.get("priority") and o["priority"] != r["priority"]:
                r["originalPriority"], r["priority"] = r["priority"], o["priority"]
    order = {"P1": 0, "P2": 1, "P3": 2}
    # Ranks come from analyze.py and stay stable across report, CSV and ledger; a review override only moves the row's tier.
    work = sorted([r for r in rows if r["action"] in ("CREATE", "REFRESH", "CONSOLIDATE")], key=lambda r: (order[r["priority"]], r["rank"]))
    review_skipped = [r for r in rows if r["action"] in ("SKIP", "MONITOR")]
    S, T, V = plan["summary"], plan["thresholds"], plan["visibility"]
    caps = T["report_caps"]
    dom = S["domain"]
    L = []
    w = L.append

    # ---------- counts, one definition shared with plan.csv ----------
    acts = Counter(r["action"] for r in work)
    comp_rows = [r for r in work if r["kind"] == "competitor"]
    counts = {"articles": len(work), "refresh": acts["REFRESH"], "create": acts["CREATE"], "consolidate": acts["CONSOLIDATE"],
              "competitor": len(comp_rows), "owner": len(owner), "protect": len(plan["protect"]), "reviewSkipped": len(review_skipped)}
    csv_rows = len(work) + len(owner) + len(plan["protect"]) + len(review_skipped)

    w(f"# Content strategy: {S.get('brand') or dom} ({dom})")
    w("")
    runs = S["aioReport"]["runs"]
    w(f"Data: Topic Clusters project \"{S['project']['label']}\" ({S['project']['createdAt'][:10]}); AIO report \"{S['aioReport']['label']}\" "
      f"(run {runs[0]['date'][:10] if runs else 'none'}" + (f", compared with {S['previousRunDate'][:10]}" if S.get("previousRunDate") else "") + "). "
      f"Market {(S['project'].get('searchParam') or {}).get('country')}/{(S['project'].get('searchParam') or {}).get('language')}/{(S['project'].get('searchParam') or {}).get('device')}. "
      f"Positions are the main keyword's, from the {S['positionSource']} unless marked (TC).")
    w("")
    if profile.get("assumptions"):
        w("> **Business profile contains assumptions.** Competitors, business values and skip terms were not confirmed by the client. "
          "See profile.json `assumptions` before sharing this report.")
        w("")

    w("## Summary")
    w("")
    if review.get("headline"):
        w(f"**{review['headline']}**")
        w("")
    w(f"- **Coverage.** {S['clusters']} clusters, {S['keywords']} keywords. The main keyword ranks top {T['rank_top']} in {S['clustersRankingTop20']} clusters; "
      f"a page of yours ranks for at least one keyword in {S['clustersWithAnyRankingPage']}.")
    sov = V["now"]
    if sov["aioKeywords"]:
        own = next(b for b in sov["brands"] if b["own"])
        ranked = sorted(sov["brands"], key=lambda b: -b["named"])
        pos = ranked.index(own) + 1
        lead = ranked[0] if ranked[0] is not own else (ranked[1] if len(ranked) > 1 else None)
        line = (f"- **AI Overviews.** {sov['aioKeywords']} of {sov['keywords']} keywords show one. You are named on {own['namedPct']}% "
                f"(#{pos} of {len(ranked)} tracked brands) and cited on {own['citedPct']}%.")
        if lead:
            line += f" {lead['brand']}: named {lead['namedPct']}%, cited {lead['citedPct']}%."
        w(line)
    w(f"- **Plan.** {counts['articles']} articles: {counts['refresh']} refresh, {counts['create']} create, {counts['consolidate']} consolidate "
      f"({counts['competitor']} of them competitor pages). Plus {counts['owner']} route-to-owner, {counts['protect']} protect"
      + (f", {counts['reviewSkipped']} removed by review" if counts["reviewSkipped"] else "") + f". plan.csv has the same {csv_rows} rows.")
    pr = Counter(r["priority"] for r in work)
    w(f"- **Priorities.** P1 {pr['P1']}, P2 {pr['P2']}, P3 {pr['P3']}. This report shows up to {caps['p1']} P1 and {caps['p2']} P2; the rest are in plan.csv.")
    if S.get("volumeFloor") is not None:
        unk = sum(1 for r in work if not r["demandKnown"])
        w(f"- **Demand unknown.** {S['clustersDemandUnknown']} of {S['clusters']} clusters have no measured demand (volume at the {S['volumeFloor']}/mo floor means not measured). "
          f"{unk} of {len(work)} articles have no measured demand; they are scored as neutral demand, cannot be P1 until sized, and P2 ones are listed separately.")
    first = [r for r in work if r["priority"] == "P1"][:3] or work[:3]
    w("- **First moves.** " + "; ".join(f"{r['action'].lower()} '{r['mainKw']}'" + (f" ({short_url(r['target'], dom)})" if r['target'] else "") for r in first) + ".")
    sc = S.get("siteCheck") or {}
    if sc.get("entries"):
        m = sc.get("methods") or {}
        how = " and ".join(f"{k.replace('websearch', 'web search')} ({v})" for k, v in m.items())
        vd = sc.get("verdicts") or {}
        w(f"- **Site check.** thruuu only sees pages in its top 20, so {sc['entries']} planned new pages were checked for an existing article by {how}. "
          f"{sc['converted']} became a refresh of a page thruuu could not see; {vd.get('owner', 0)} found only a help, product or pricing page; {vd.get('related', 0)} found a related page to link. See site-check.md.")
    if S["notes"]:
        w("- **Data notes.** " + " ".join(S["notes"]))
    if not S.get("hasPreviousRun"):
        w("- **Baseline.** No earlier AIO run to compare with. Schedule the report monthly to track movement.")
    w("")

    w("## How to read this")
    w("")
    w("- **REFRESH**: a page of yours already ranks; improve that URL. **CREATE**: no suitable page; write one. **CONSOLIDATE**: two of your pages compete for one cluster; merge into the target URL.")
    w("- **Priority** P1 (do now), P2 (this quarter), P3 (backlog) comes from one score: demand x opportunity x competition x AI Overview gap x business value. The breakdown per row is in plan.csv `score_breakdown`.")
    w("- **Position** is your position on the row's main keyword. \"not ranking (page best #N)\" means the page ranks only for other keywords of the cluster.")
    w("- **AIO** is the AI Overview on the main keyword only: who it names, and whether it names or cites you.")
    w(f"- **Next step** for every row: open the cluster in the thruuu Topic Clusters project \"{S['project']['label']}\", run Cluster Analysis, then create the brief in thruuu. The brief works out the page's outline and format from each keyword's own results; a cluster's Mixed SERP blends all its keywords' results, so it is not the results page of any single keyword.")
    w("- **Flags** (plan.csv): SOURCES_DISAGREE (Topic Clusters and the AIO report disagree; capped at P2), STALE_POSITION (Topic Clusters position older than "
      f"{T['stale_tc_days']} days), SOURCE_CONFLICT (they name different URLs), CANNIBALISATION, SHARED_PAGE, OFF_TOPIC_PAGE, CHECK_SIBLING_PAGE (a page in the same category already ranks), "
      "FOUND_BY_SITE_SEARCH / FOUND_IN_SITEMAP (an existing page outside thruuu's top 20 was found, so the row refreshes it), OWNER_PAGE_FOUND (only a help, product or pricing page exists), RELATED_PAGE_FOUND (link to it), "
      "RANKS_NOT_CITED (you rank top 10 on one of the row's keywords, its AI Overview cites other pages).")
    w("")

    # ---------- AI Overview visibility ----------
    if sov["aioKeywords"]:
        prev = V.get("previous")
        pb = {b["brand"]: b for b in (prev or {}).get("brands", [])}
        w("## AI Overview visibility")
        w("")
        w(f"Across the {sov['aioKeywords']} keywords with an AI Overview. Named = the brand appears in the answer text. Cited = a page on its domain is a source.")
        w("")
        w("| Brand | Named | Cited |" + (" Named change | Cited change |" if prev else ""))
        w("|---|---|---|" + ("---|---|" if prev else ""))
        for b in sorted(sov["brands"], key=lambda b: -b["named"]):
            name = f"**{b['brand']}** (you)" if b["own"] else b["brand"]
            row = f"| {name} | {b['named']} ({b['namedPct']}%) | {b['cited']} ({b['citedPct']}%) |"
            if prev:
                q = pb.get(b["brand"], {"named": 0, "cited": 0})
                row += f" {b['named'] - q['named']:+d} | {b['cited'] - q['cited']:+d} |"
            w(row)
        w("")
        own = next(b for b in sov["brands"] if b["own"])
        lead = max((b for b in sov["brands"] if not b["own"]), key=lambda b: b["cited"], default=None)
        if lead and own["cited"]:
            w(f"{lead['brand']} is cited {lead['cited'] / own['cited']:.1f}x as often as you and named {lead['named'] / max(own['named'], 1):.1f}x as often.")
            w("")
        w("### Who the AI cites")
        w("")
        w("| Domain | Type | AIO keywords citing it | Where you are not cited |" + (" Change |" if V.get("citedDomainsPrevious") else ""))
        w("|---|---|---|---|" + ("---|" if V.get("citedDomainsPrevious") else ""))
        for d in V["citedDomains"]:
            cls = d["class"] + (f" ({d['competitor']})" if d.get("competitor") else "")
            row = f"| {d['domain']} | {cls} | {d['keywords']} | {d['whereOwnNotCited']} |"
            if V.get("citedDomainsPrevious"):
                row += f" {d['keywords'] - V['citedDomainsPrevious'].get(d['domain'], 0):+d} |"
            w(row)
        w("")
        named_not_cited = [r for r in work if r["aio"]["head"] == "named_not_cited"]
        if named_not_cited:
            w("**Named but not cited** (the AI recommends you and links someone else): " + "; ".join(f"#{r['rank']} {r['mainKw']}" for r in named_not_cited) + ".")
            w("")

    def table(rs):
        w("| # | Pri | Action | Target keyword | Target URL | Pos | Demand/mo | AIO | Why (data) | Effort |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for r in rs:
            act = r["action"] + (" (competitor)" if r["kind"] == "competitor" else "") + (f" (was {r['originalAction']})" if r.get("originalAction") else "")
            pri = r["priority"] + (f" (was {r['originalPriority']})" if r.get("originalPriority") else "")
            why = r["rationale"] + (f" **Reviewer:** {r['reviewNote']}" if r.get("reviewNote") else "") + f" **{next_step(r)}**"
            w(f"| {r['rank']} | {pri} | {act} | {md(r['mainKw'])} | {md(target_cell(r, dom))} | {pos_cell(r)} | {n(r['volume'])} | {md(aio_cell(r))} | {md(why)} | {r['effort']} |")

    p1 = [r for r in work if r["priority"] == "P1"]
    p2 = [r for r in work if r["priority"] == "P2" and r["demandKnown"]]
    p2u = [r for r in work if r["priority"] == "P2" and not r["demandKnown"]]
    w(f"## P1: do now ({min(len(p1), caps['p1'])} of {len(p1)})")
    w("")
    table(p1[:caps["p1"]]) if p1 else w("None. Nothing clears the P1 bar on measured demand this run.")
    w("")
    shown_p2 = p2[:caps["p2"]]
    u_slots = max(0, caps["p2"] - len(shown_p2))
    w(f"## P2: this quarter ({len(shown_p2)} of {len(p2)} with measured demand)")
    w("")
    table(shown_p2) if shown_p2 else w("None.")
    w("")
    if p2u:
        k = min(len(p2u), max(u_slots, 5))
        w(f"## Demand unknown: size before deciding ({k} of {len(p2u)} P2 rows)")
        w("")
        w("These score like P2 on everything except demand, which thruuu could not measure. Check volume in your keyword tool or Search Console before briefing.")
        w("")
        table(p2u[:k])
        w("")
    rest = len(work) - min(len(p1), caps["p1"]) - len(shown_p2) - (min(len(p2u), max(u_slots, 5)) if p2u else 0)
    w(f"{rest} more articles (remaining P1/P2 and all P3) are in plan.csv only.")
    w("")

    if comp_rows:
        w("## Competitor pages")
        w("")
        w("Comparison, alternatives and pricing queries grouped into one page per competitor. Queries about a competitor's own product are skipped (profile `conquest.navigational`).")
        w("")
        for r in comp_rows:
            w(f"- **{r['competitor']}** (#{r['rank']}, {r['priority']}, {r['action'].lower()} {target_cell(r, dom)}): {len(r['clusters'])} {'query' if len(r['clusters']) == 1 else 'queries'}, demand {n(r['volume']) + '/mo' if r['volume'] is not None else 'not measured'}. "
              f"Examples: {'; '.join([r['mainKw']] + r['secondaryKeywords'][:3])}.")
        w("")

    g_rows = [r for r in work if r["priority"] in ("P1", "P2") and r["demandKnown"]][:caps["p1"] + caps["p2"]]
    if g_rows:
        w("## Content guidance (P1 and P2)")
        w("")
        w(f"Evidence to steer each article, not a brief: no outline, headings or word counts. Each line names its source: **keyword top 10** is the exact results page of one keyword (AIO report, main keyword plus up to {T['top10_per_cluster'] - 1} AIO keywords); "
          "**cluster Mixed SERP** blends the results of all the cluster's keywords.")
        w("")
        for r in g_rows:
            w(f"**#{r['rank']} {r['mainKw']}**")
            w("")
            for line in (r.get("reviewGuidance") or guidance_lines(r)):
                w(f"- {line}")
            w(f"- {next_step(r)}")
            w("")

    if plan.get("offsite"):
        w("## Off-site actions (not articles)")
        w("")
        w(f"Domains the AI cites on {T['offsite_min_keywords']}+ keywords where you are not cited. Work these alongside the articles.")
        w("")
        w("| Domain | Type | Keywords where it is cited and you are not | Action | Example cited page |")
        w("|---|---|---|---|---|")
        for d in plan["offsite"]:
            w(f"| {d['domain']} | {d['class']} | {d['whereOwnNotCited']} | {d['action']} | {md(d['topUrls'][0] if d['topUrls'] else '')} |")
        w("")

    if owner:
        w("## Route to owner (help, product and home pages)")
        w("")
        w("These rank with a page the content team does not own. Send them to the page's owner; do not write a competing article.")
        w("")
        for r in owner:
            w(f"- {short_url(r['target'], dom)}: '{r['mainKw']}' {pos_cell(r)}, demand {n(r['volume']) + '/mo' if r['volume'] is not None else 'not measured'}. {r.get('reviewNote') or ''}".rstrip())
        w("")

    if plan["protect"]:
        by = {c["id"]: c for c in plan["clusters"]}
        w("## Protect (no action, monitor)")
        w("")
        for m in plan["protect"]:
            w(f"- {m['key'].split(':', 1)[1]}: " + "; ".join(f"{by[i]['mainKw']} (#{by[i]['headPos']})" for i in m["clusters"]))
        w("")

    if plan["skipped"] or review_skipped:
        w("## Skipped")
        w("")
        reasons = Counter(s["reason"].split(":")[0] if s["reason"].startswith("profile") else s["reason"].split(" (")[0] for s in plan["skipped"])
        w(f"{len(plan['skipped'])} clusters skipped by rule: " + "; ".join(f"{k} ({v})" for k, v in reasons.most_common()) + ". Full list in plan.json `skipped`.")
        for r in review_skipped:
            w(f"- Removed by review: {r['mainKw']} ({r['action']}, was {r.get('originalAction')}). {r.get('reviewNote', '')}")
        w("")
    if plan.get("parked"):
        w(f"{len(plan['parked'])} uncategorised clusters with no measured demand are parked (plan.json `parked`).")
        w("")

    w("## Method")
    w("")
    w("One row = one page. Pages that already rank are grouped by URL. New pages are grouped by category: one hub, related questions as sections, other clusters with demand as supporting pages. "
      f"Competitor comparison queries get one page per competitor. Position bands: 1 to {T['position_bands']['protect_max']} protect, to {T['position_bands']['striking_max']} striking distance, "
      f"to {T['position_bands']['page_two_max']} page two, to {T['position_bands']['rewrite_max']} rewrite. P1 needs score {T['priority']['p1_min']}+ on {n(T['priority']['p1_min_volume'])}/mo measured demand; "
      f"P2 needs {T['priority']['p2_min']}+. Next step for any row: open the cluster in thruuu, run Cluster Analysis, then create the brief there.")
    w("")

    with open(os.path.join(out, "strategy-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L).replace("\u2014", "-").replace("\u2013", "-"))

    cols = ["rank", "priority", "action", "kind", "competitor", "mainKw", "category", "intent", "target", "existing_weak_page", "position", "position_source",
            "best_evidence", "demand_known", "volume", "keyword_count", "competition", "average_pr", "aio_main_keyword", "competitors_named", "score",
            "score_breakdown", "effort", "flags", "format", "secondary_keywords", "questions_to_fold", "supporting_pages", "protect", "consolidate_from",
            "rationale", "success_check", "review_note", "ledger_key", "cluster_id", "site_check", "next_step", "aio_themes", "content_guidance"]
    with open(os.path.join(out, "plan.csv"), "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f)
        cw.writerow(cols)
        by = {c["id"]: c for c in plan["clusters"]}
        for r in work + owner + review_skipped:
            be = r.get("bestEvidence") or {}
            cw.writerow([r.get("rank", ""), r["priority"], r["action"], r["kind"], r.get("competitor", ""), r["mainKw"], r["category"], r["intent"], r["target"] or "",
                         r.get("existingWeakPage") or "", r["position"] if r["position"] is not None else "", r.get("posSource") or "",
                         f"#{be['position']} on {be['keyword']}" if be.get("position") else "", r["demandKnown"], r["volume"] if r["volume"] is not None else "",
                         r["keywordCount"], r["competition"], r["averagePR"], aio_cell(r), "; ".join(c for c, _ in r["aio"]["competitors"]), r["score"],
                         r["scoreBreakdown"], r["effort"], "; ".join(r["flags"]), "; ".join(r["format"]), "; ".join(r["secondaryKeywords"]),
                         "; ".join(r["questionsToFold"]), "; ".join(f"{s['mainKw']} ({n(s['volume'])})" for s in r.get("supportingPages", [])),
                         "; ".join(r["protectKeywords"]), "; ".join(r.get("consolidateFrom", [])), r["rationale"], r["successCheck"],
                         r.get("reviewNote", ""), r["key"], r["clusterId"],
                         (lambda sc: f"{sc['verdict']}: {sc['url']} ({sc['method']}, {sc.get('checkedAt') or ''})" if sc else "")(r.get("siteCheck")),
                         next_step(r) if r["action"] in ("CREATE", "REFRESH", "CONSOLIDATE") else "",
                         ", ".join((r.get("guide") or {}).get("themes") or []),
                         " ".join(r.get("reviewGuidance") or guidance_lines(r))])
        for m in plan["protect"]:
            c0 = by[m["clusters"][0]]
            cw.writerow(["", "", "MONITOR", "protect", "", c0["mainKw"], c0["category"], c0["intent"], m["key"].split(":", 1)[1], "", c0["headPos"], c0["posSource"], "",
                         c0["volumeKnown"], c0["volume"] if c0["volume"] is not None else "", c0["count"], "", c0["averagePR"], "", "", "", "", "", "", "", "", "", "", "", "",
                         "Top 3 on the main keyword with no AI Overview gap.", "", "", m["key"], c0["id"], "", "", "", ""])
    print(f"Wrote {os.path.join(out, 'strategy-report.md')} and plan.csv ({csv_rows} rows: {counts}).")


if __name__ == "__main__":
    main()
