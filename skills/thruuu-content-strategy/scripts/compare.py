#!/usr/bin/env python3
"""Compare this run's plan with the previous one, evaluate success checks, and keep the ledger.

  python3 compare.py --current RUN/plan.json [--previous PREV/plan.json] --ledger WORKSPACE/ledger.json
                     [--review RUN/review.json] [--out RUN/changes.md]

Rows are keyed by a stable key: `url:` for pages that exist, `cluster:` (hub cluster id) for new
pages, `competitor:` for competitor pages. When a key changes (a new page starts ranking and the row
becomes `url:`), the match falls back to shared cluster ids and the ledger status is carried over.
Entries not seen this run are marked stale, never deleted. Re-running on the same pair is idempotent.
"""
import argparse
import datetime as dt
import json
import os
import re
from collections import Counter

STATUSES = {"proposed", "planned", "in_progress", "published", "dropped"}
LABEL = {None: "no AI Overview", "absent": "names no brand", "absent_competitors_named": "names competitors, not you",
         "named_not_cited": "names you, cites others", "cited_not_named": "cites you without naming you", "named_and_cited": "names and cites you"}


def load(p, default=None):
    if not p or not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def nk(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def match_rows(prev_rows, cur_rows):
    """Map current row key -> (previous row, how matched). Exact keys first, then shared primary cluster, then main keyword."""
    by_key = {r["key"]: r for r in prev_rows}
    out, used = {}, set()
    for r in cur_rows:
        if r["key"] in by_key:
            out[r["key"]] = (by_key[r["key"]], "key")
            used.add(r["key"])

    def work_ids(x):
        return set(x.get("clusters") or [x.get("clusterId")]) | {i for i in (x.get("supportingIds") or [])}
    for r in cur_rows:
        if r["key"] in out:
            continue
        p = next((q for q in prev_rows if q["key"] not in used and (q.get("clusterId") in work_ids(r) or r.get("clusterId") in work_ids(q))), None)
        how = "shared primary cluster"
        if not p:
            p = next((q for q in prev_rows if q["key"] not in used and nk(q["mainKw"]) == nk(r["mainKw"])), None)
            how = "main keyword"
        if p:
            used.add(p["key"])
            out[r["key"]] = (p, how)
    return out, used


def evaluate(success, cur_plan, margin):
    """met / partly met / regressed / not yet, from the current run's cluster data."""
    by_id = {c["id"]: c for c in cur_plan["clusters"]}
    c = by_id.get(success["clusterId"]) or next((x for x in cur_plan["clusters"] if nk(x["mainKw"]) == nk(success["keyword"])), None)
    if not c:
        return "unknown", "cluster not in this run"
    pos, base, tgt = c["headPos"], success.get("baselinePos"), success["targetPos"]
    new_url = not success.get("baselineUrl") or (c.get("target") and c["target"] != success["baselineUrl"])
    rank_ok = pos is not None and pos <= tgt and new_url and (base is None or pos < base or (base <= tgt and success.get("aioKeywords")))
    aio_ok = True
    if success.get("aioKeywords"):
        st = {nk(k): v for k, v in c.get("kwStates", {}).items()}
        aio_ok = any((st.get(nk(k)) or {}).get("mentioned") or (st.get(nk(k)) or {}).get("cited") for k in success["aioKeywords"])
    now = f"#{pos}" if pos is not None else "not ranking"
    if rank_ok and aio_ok:
        return "met", f"'{success['keyword']}' now {now} (target top {tgt})"
    if rank_ok:
        return "partly met", f"'{success['keyword']}' now {now}; AI Overview not yet naming or citing you"
    if base is not None and (pos is None or pos > base + margin):
        return "regressed", f"'{success['keyword']}' was #{base}, now {now}"
    return "not yet", f"'{success['keyword']}' {('was #' + str(base) + ', ') if base else ''}now {now} (target top {tgt})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current", required=True)
    ap.add_argument("--previous")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--review")
    ap.add_argument("--out")
    a = ap.parse_args()
    cur = load(a.current)
    prev = load(a.previous)
    review = load(a.review, {}) or {}
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.current)), "changes.md")
    ledger = load(a.ledger, {"version": 2, "rows": {}, "runs": []})
    S = cur["summary"]
    run_id = S.get("runDate") or S.get("pulledAt") or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    margin = cur["thresholds"].get("success_regress_margin", 3)
    rev_skip = {k for k, v in (review.get("rows") or {}).items() if v.get("action") == "SKIP"}

    def protect_rows(plan):
        by = {c["id"]: c for c in plan["clusters"]}
        return [{"key": m["key"], "mainKw": by[m["clusters"][0]]["mainKw"], "action": "MONITOR", "priority": "-", "clusterId": m["clusters"][0], "clusters": m["clusters"],
                 "memberClusterIds": m["clusters"], "position": by[m["clusters"][0]]["headPos"], "target": None, "aio": {"head": by[m["clusters"][0]]["aio"]["head"]}}
                for m in plan.get("protect", [])]

    cur_rows = cur["rows"] + cur.get("ownerRows", []) + protect_rows(cur)
    L = []
    w = L.append
    w(f"# Changes since last run: {S.get('brand') or S['domain']}")
    w("")

    matches, used = ({}, set())
    if prev:
        prev_rows = prev["rows"] + prev.get("ownerRows", []) + protect_rows(prev)
        matches, used = match_rows(prev_rows, cur_rows)
        w(f"Previous run: {(prev['summary'].get('runDate') or '')[:10]}. This run: {run_id[:10]}.")
        w("")

        # Wins first: success checks met, new pages that now rank, AI Overview gains.
        evals = []
        for p in prev_rows:
            if p.get("success") and p["action"] in ("CREATE", "REFRESH", "CONSOLIDATE", "ROUTE"):
                st, detail = evaluate(p["success"], cur, margin)
                evals.append((p, st, detail))
        found_flags = {"FOUND_BY_SITE_SEARCH", "FOUND_IN_SITEMAP"}
        became_all = [(r, m[0]) for r in cur_rows for m in [matches.get(r["key"])] if m and m[0]["action"] == "CREATE" and r["action"] in ("REFRESH", "CONSOLIDATE")]
        became = [(r, p) for r, p in became_all if not found_flags & set(r.get("flags") or [])]
        site_found = [(r, p) for r, p in became_all if found_flags & set(r.get("flags") or [])]
        ev = S.get("aioEvents") or []
        gains = [e for e in ev if e["event"] in ("gained mention", "gained citation")]
        w("## Wins")
        w("")
        wins = [x for x in evals if x[1] == "met"]
        for p, _, d in wins:
            w(f"- Success check met: {d} ({p['action'].lower()} {p.get('target') or 'new page'}).")
        for r, p in became:
            w(f"- New page now ranks: '{r['mainKw']}' moved from CREATE to {r['action']} on {r['target']}.")
        for r, p in site_found:
            w(f"- Not a win, a correction: '{r['mainKw']}' moved from CREATE to {r['action']} because the site check found {r['target']} (outside thruuu's top 20).")
        now_protected = [(r, m[0]) for r in cur_rows for m in [matches.get(r["key"])] if m and r["action"] == "MONITOR" and m[0]["action"] != "MONITOR"]
        for r, p in now_protected:
            w(f"- Now protected: {r['key'].split(':', 1)[1]} ('{r['mainKw']}' #{r['position']}) no longer needs work (was {p['action']} {p['priority']}).")
        if gains:
            w(f"- AI Overview gains: {len([e for e in gains if e['event'] == 'gained mention'])} new mentions, "
              f"{len([e for e in gains if e['event'] == 'gained citation'])} new citations, on: " + "; ".join(e["keyword"] for e in gains[:10]) + ".")
        if not (wins or became or site_found or gains or now_protected):
            w("- None this run.")
        w("")

        w("## Success checks from the previous plan")
        w("")
        cnt = Counter(st for _, st, _ in evals)
        w("Met " + str(cnt["met"]) + ", partly met " + str(cnt["partly met"]) + ", not yet " + str(cnt["not yet"]) + ", regressed " + str(cnt["regressed"]) + ", unknown " + str(cnt["unknown"]) + ".")
        for p, st, d in evals:
            if st in ("regressed", "partly met"):
                w(f"- **{st}**: {d}.")
        w("")

        # Metrics and competitor movement.
        w("## Metrics")
        w("")
        w("| Metric | Previous | Now | Change |")
        w("|---|---|---|---|")
        pv, cv = prev["visibility"]["now"], cur["visibility"]["now"]

        def row(label, a_, b_):
            d = (b_ - a_) if isinstance(a_, (int, float)) and isinstance(b_, (int, float)) else None
            w(f"| {label} | {a_} | {b_} | {'n/a' if d is None else f'{d:+}'} |")
        row("Keywords with an AI Overview", pv["aioKeywords"], cv["aioKeywords"])
        po = next(b for b in pv["brands"] if b["own"])
        co = next(b for b in cv["brands"] if b["own"])
        row("You: named (% of AIO keywords)", po["namedPct"], co["namedPct"])
        row("You: cited (% of AIO keywords)", po["citedPct"], co["citedPct"])
        row("Clusters with main keyword top 20", prev["summary"]["clustersRankingTop20"], S["clustersRankingTop20"])
        row("Articles in plan", len([r for r in prev["rows"]]), len(cur["rows"]))
        w("")
        w("### Competitor movement in AI Overviews")
        w("")
        w("| Brand | Named then | Named now | Cited then | Cited now |")
        w("|---|---|---|---|---|")
        pb = {b["brand"]: b for b in pv["brands"]}
        for b in sorted(cv["brands"], key=lambda b: -b["named"]):
            q = pb.get(b["brand"], {"namedPct": 0, "citedPct": 0})
            w(f"| {b['brand']}{' (you)' if b['own'] else ''} | {q['namedPct']}% | {b['namedPct']}% | {q['citedPct']}% | {b['citedPct']}% |")
        w("")
        losses = [e for e in ev if e["event"] in ("lost mention", "lost citation")]
        if losses:
            w("### Lost in AI Overviews")
            w("")
            w("; ".join(f"{e['keyword']} ({e['event']})" for e in losses[:20]) + ".")
            w("")

        w("## Moved")
        w("")
        moved = 0
        for r in cur_rows:
            m = matches.get(r["key"])
            if not m:
                continue
            p, how = m
            notes = []
            if nk(p["mainKw"]) != nk(r["mainKw"]):
                notes.append(f"main keyword changed from '{p['mainKw']}' to '{r['mainKw']}' (not a ranking loss)")
            elif p.get("position") != r.get("position"):
                notes.append(f"position {('#' + str(p['position'])) if p.get('position') else 'not ranking'} to {('#' + str(r['position'])) if r.get('position') else 'not ranking'}")
            if p["action"] != r["action"]:
                notes.append(f"action {p['action']} to {r['action']}")
            if p["priority"] != r["priority"]:
                notes.append(f"priority {p['priority']} to {r['priority']}")
            if p["aio"].get("head") != r["aio"].get("head"):
                notes.append(f"AI Overview on main keyword: {LABEL.get(p['aio'].get('head'))} to {LABEL.get(r['aio'].get('head'))}")
            if how != "key":
                notes.append(f"matched by {how}")
            if notes:
                moved += 1
                w(f"- **{r['mainKw']}** (#{r.get('rank', '')} {r['priority']}): " + "; ".join(notes) + ".")
        if not moved:
            w("- Nothing moved.")
        w("")

        w("## New in the plan")
        w("")
        new = [r for r in cur_rows if r["key"] not in matches]
        w("\n".join(f"- {r['mainKw']} ({r['action']}, {r['priority']})" for r in new) or "- None.")
        w("")
        w("## Left the plan")
        w("")
        skipped = {s["clusterId"]: s["reason"] for s in cur.get("skipped", [])}
        protected = {i for m in cur.get("protect", []) for i in m["clusters"]}
        left = [p for p in prev_rows if p["key"] not in used]
        for p in left:
            ids = set(p.get("memberClusterIds") or [p["clusterId"]])
            if p["key"] in rev_skip:
                why = "removed by review this run"
            elif ids & set(skipped):
                why = "skipped: " + skipped[next(iter(ids & set(skipped)))]
            elif ids & protected:
                why = "now protected (main keyword top 3, no AI Overview gap)"
            else:
                why = "its clusters are no longer in the data (re-clustered or hidden)"
            w(f"- {p['mainKw']} (was {p['action']} {p['priority']}): {why}.")
        if not left:
            w("- None.")
        w("")
    else:
        w("Baseline run: no previous plan. The next run compares against this one, evaluates each row's success check and reports wins.")
        w("")

    # ---------- ledger ----------
    rows = ledger["rows"]
    for r in cur_rows:
        k = r["key"]
        m = matches.get(k)
        if k not in rows and m and m[0]["key"] in rows and m[0]["key"] != k:
            old = rows.pop(m[0]["key"])
            old["notes"] = (old.get("notes", "") + f" Carried from {m[0]['key']} ({m[1]}).").strip()
            rows[k] = old
        e = rows.setdefault(k, {"mainKw": r["mainKw"], "status": "proposed", "firstSeen": run_id, "notes": ""})
        hist = [h for h in e.get("history", []) if h["run"] != run_id]
        hist.append({"run": run_id, "action": r["action"], "priority": r["priority"], "position": r.get("position")})
        e.update({"mainKw": r["mainKw"], "lastSeen": run_id, "action": r["action"], "priority": r["priority"], "target": r.get("target"),
                  "position": r.get("position"), "memberClusterIds": r.get("memberClusterIds"), "stale": False, "history": hist,
                  "reviewSkipped": k in rev_skip})
        if e.get("status") not in STATUSES:
            e["status"] = "proposed"
    for k, e in rows.items():
        if e.get("lastSeen") != run_id:
            e["stale"] = True
    ledger["runs"] = [x for x in ledger.get("runs", []) if x.get("run") != run_id] + [{"run": run_id, "rows": len(cur_rows)}]

    w("## Ledger")
    w("")
    counts = Counter(e["status"] for e in rows.values() if not e.get("stale"))
    w("Status counts (current rows): " + ", ".join(f"{s} {counts.get(s, 0)}" for s in sorted(STATUSES)) + f". Stale entries kept: {sum(1 for e in rows.values() if e.get('stale'))}. Edit `status` in ledger.json as work ships.")
    pub_create = [e for e in rows.values() if e["status"] == "published" and not e.get("stale") and e.get("action") == "CREATE"]
    done_now = [e for e in rows.values() if e["status"] in ("planned", "in_progress") and not e.get("stale") and e.get("action") == "MONITOR"]
    if done_now:
        w("")
        w("Planned or in progress but the data says the page is now protected (top 3, no AI Overview gap). Consider marking them published:")
        for e in done_now:
            w(f"- {e['mainKw']}")
    if pub_create:
        w("")
        w("Marked published but still CREATE (no page of yours ranks yet). Check indexing and internal links:")
        for e in pub_create:
            w(f"- {e['mainKw']}")
    w("")
    os.makedirs(os.path.dirname(os.path.abspath(a.ledger)), exist_ok=True)
    with open(a.ledger, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=1)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"Wrote {out} and {a.ledger}. {'Baseline.' if not prev else f'{len(matches)} matched, {len(cur_rows) - len(matches)} new, {len(prev_rows) - len(used)} left.'}")


if __name__ == "__main__":
    main()
