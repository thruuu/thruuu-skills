#!/usr/bin/env python3
"""Pull thruuu Topic Clusters + AIO Monitoring data into a local snapshot folder.

GET requests only. Never triggers a scrape, never spends credits.

Subcommands:
  check                               validate THRUUU_API_KEY / THRUUU_API_BASE
  list [--all]                        list usable Topic Cluster projects and AIO reports, with pairing hints
  snapshot --project ID --report ID --out DIR [--as-of RESULT_ID] [--gap-days N] [--no-previous] [--domains-max 200] [--top10-per-cluster 3]
  details  --project ID --snapshot DIR (--clusters ID[,ID...] | --plan plan.json [--priorities P1,P2] [--max 15]) [--mixed-serp-only]
  keyword  --report ID [--result RESULT_ID] [--snapshot DIR] [--fresh] "<keyword>"
                                      one keyword's full AIO data: AI text, sources, brands, themes, top 10 organic
"""
import argparse
import datetime as dt
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thruuu_api import ApiError, Client  # noqa: E402

HEAVY_FIELDS = ("body", "kwBody", "semanticBody", "anchors", "images", "og")
KW_INCLUDE = "aiOverview,topOrganicResults"  # one comma-separated include; a repeated include param is a 400


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def host(domain):
    d = (domain or "").lower().strip()
    for p in ("https://", "http://"):
        if d.startswith(p):
            d = d[len(p):]
    d = d.split("/")[0]
    return d[4:] if d.startswith("www.") else d


def parse_date(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def cmd_check(c, _):
    try:
        a = c.get("/aio-reports", {"itemsPerPage": 1})
        print(f"OK AIO Monitoring API: {a.get('total', 0)} report(s) visible.")
    except ApiError as e:
        print(f"AIO Monitoring API: {e}")
    try:
        t = c.get("/topic-clusters", {"itemsPerPage": 1})
        print(f"OK Topic Clusters API: {t.get('total', 0)} project(s) visible.")
    except ApiError as e:
        print(f"Topic Clusters API: {e}")
    print(f"Base URL: {c.base}")


def cmd_list(c, a):
    projects = list(c.paginate("/topic-clusters", "items", 100))
    reports = list(c.paginate("/aio-reports", "items", 100))
    usable_p = [p for p in projects if a.all or (p.get("domain") and p.get("status") == "Done")]
    usable_r = [r for r in reports if a.all or (r.get("resultsTotal") or 0) > 0]
    failed = sum(1 for p in projects if p.get("status") == "Failed" and p not in usable_p)
    other = len(projects) - len(usable_p) - failed
    print(f"TOPIC CLUSTER PROJECTS ({len(usable_p)} shown, {other} hidden: no domain or not Done, {failed} failed; --all to show)")
    for p in usable_p:
        sp = p.get("searchParam") or {}
        print(f"  {p['id']}  {p['status']:<11} {p['createdAt'][:10]}  domain={p.get('domain')}  "
              f"{sp.get('country')}/{sp.get('language')}/{sp.get('device')}  clusters={p.get('clusterCount')}  "
              f"keywords={p.get('keywordCount')}  \"{p.get('label')}\"")
    print(f"AIO REPORTS ({len(usable_r)} shown, {len(reports) - len(usable_r)} hidden: no completed run)")
    for r in usable_r:
        sp = r.get("searchParam") or {}
        freq = (r.get("schedule") or {}).get("frequency")
        print(f"  {r['id']}  {r['type']:<9} runs={r.get('resultsTotal')}  freq={freq}  {r['createdAt'][:10]}  "
              f"brand={r.get('brandName')} domain={r.get('domain')}  {sp.get('country')}/{sp.get('language')}/{sp.get('device')}  "
              f"\"{r.get('label')}\"")
    print("PAIRING HINTS (same domain, country, language, device; newest first)")
    found = False
    for p in usable_p:
        shown = 0
        for r in usable_r:
            if shown >= 3:
                break
            ps, rs = p.get("searchParam") or {}, r.get("searchParam") or {}
            if (host(p.get("domain")) == host(r.get("domain"))
                    and ps.get("country") == rs.get("country") and ps.get("language") == rs.get("language")
                    and ps.get("device") == rs.get("device")):
                found = True
                shown += 1
                print(f"  project {p['id']} \"{p.get('label')}\"  <->  report {r['id']} \"{r.get('label')}\"")
    if not found:
        print("  none found. Pair manually, and check both use the same market and keyword list.")
    print(f"({c.calls} API calls)")


def pick_runs(c, report_id, as_of, gap_days, want_previous):
    """Return (current, previous) run dicts from the run list, as of a given run, previous at least gap_days older."""
    runs = (c.get(f"/aio-reports/{report_id}/runs", {"runs": 365}) or {}).get("runs") or []
    if not runs:
        return None, None, runs
    idx = 0
    if as_of:
        idx = next((i for i, r in enumerate(runs) if r["resultId"] == as_of), None)
        if idx is None:
            sys.exit(f"Run {as_of} not found among the last {len(runs)} completed runs of report {report_id}.")
    cur = runs[idx]
    prev = None
    if want_previous:
        limit = parse_date(cur["date"]) - dt.timedelta(days=gap_days)
        prev = next((r for r in runs[idx + 1:] if parse_date(r["date"]) <= limit), None)
    return cur, prev, runs


def cmd_snapshot(c, a):
    out = a.out
    os.makedirs(out, exist_ok=True)
    warnings = []

    project = c.get(f"/topic-clusters/{a.project}")
    if project.get("status") == "Failed":
        sys.exit(f"Topic Cluster project {a.project} failed in thruuu, so its data is incomplete. Rerun it in thruuu, then pull again.")
    write(os.path.join(out, "tc_project.json"), project)
    if project.get("status") != "Done":
        warnings.append(f"Topic Cluster project status is {project.get('status')}, not Done.")
    if not project.get("domain"):
        warnings.append("Topic Cluster project has no domain: no ranking fields. Actions will lean on AIO data only.")

    clusters = list(c.paginate(f"/topic-clusters/{a.project}/clusters", "items", 150))
    write(os.path.join(out, "tc_clusters.json"), clusters)

    domains = []
    for row in c.paginate(f"/topic-clusters/{a.project}/domains", "items", 100):
        domains.append(row)
        if len(domains) >= a.domains_max:
            break
    write(os.path.join(out, "tc_domains.json"), domains)

    cur, prev, all_runs = pick_runs(c, a.report, a.as_of, a.gap_days, not a.no_previous)
    run_files = []
    if not cur:
        warnings.append("AIO report has no completed run. AIO overlay disabled.")
        report = c.get(f"/aio-reports/{a.report}", {"runs": 1})
        report["runs"] = []
    else:
        chosen = [r for r in (cur, prev) if r]
        depth = max(all_runs.index(r) for r in chosen) + 1
        report = c.get(f"/aio-reports/{a.report}", {"runs": depth, "topN": 100})
        keep = {r["resultId"] for r in chosen}
        report["runs"] = [r for r in report.get("runs") or [] if r["resultId"] in keep]
        for i, run in enumerate(chosen):
            rid = run["resultId"]
            kws = list(c.paginate(f"/aio-reports/{a.report}/runs/{rid}/keywords", "keywords", 200, {"include": "aiOverview"}))
            name = "aio_keywords_latest.json" if i == 0 else "aio_keywords_previous_1.json"
            write(os.path.join(out, name), {"run": {"resultId": rid, "date": run.get("date")}, "keywords": kws})
            run_files.append({"file": name, "resultId": rid, "date": run.get("date"), "keywords": len(kws)})
            if i == 0 and a.top10_per_cluster > 0:
                top10 = pull_top10(c, a.report, rid, clusters, kws, a.top10_per_cluster)
                write(os.path.join(out, "aio_top10_latest.json"), {"run": {"resultId": rid, "date": run.get("date")}, **top10})
                run_files.append({"file": "aio_top10_latest.json", **top10["log"]})
        if not a.no_previous and not prev:
            warnings.append("AIO report has no earlier run matching the gap: no run-over-run movement this time (baseline).")
    write(os.path.join(out, "aio_report.json"), report)

    rep = report.get("report") or {}
    ps, rs = project.get("searchParam") or {}, rep.get("searchParam") or {}
    for k in ("country", "language", "device"):
        if ps.get(k) != rs.get(k):
            warnings.append(f"Market mismatch on {k}: project={ps.get(k)} report={rs.get(k)}. Joined signals may disagree.")
    if host(project.get("domain")) != host(rep.get("domain")):
        warnings.append(f"The AIO report tracks {rep.get('brandName')} ({rep.get('domain')}), not the project domain. "
                        "Your mentions and citations are derived from each AI Overview's brands and sources; "
                        "organic positions come from Topic Clusters only.")

    manifest = {
        "pulledAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "base": c.base,
        "projectId": a.project,
        "reportId": a.report,
        "asOf": a.as_of,
        "gapDays": a.gap_days,
        "clusters": len(clusters),
        "domains": len(domains),
        "aioRuns": run_files,
        "warnings": warnings,
        "apiCalls": c.calls,
    }
    write(os.path.join(out, "manifest.json"), manifest)
    print(json.dumps(manifest, indent=1))


def select_top10(clusters, kws, per_cluster):
    """Per cluster: the main keyword, then its highest-volume keywords that have an AI Overview, up to per_cluster."""
    idx = {norm_kw(k.get("keyword")): k for k in kws}
    sel = {}
    for cl in clusters:
        if cl.get("hidden"):
            continue
        main = norm_kw(cl.get("mainKw"))
        others = [norm_kw(k) for k in cl.get("similarity") or [] if norm_kw(k) != main and (idx.get(norm_kw(k)) or {}).get("hasAIO")]
        others.sort(key=lambda k: -(idx[k].get("volume") or 0))
        for role, k in [("main", main)] + [("aio", k) for k in others[:per_cluster - 1]]:
            if k in idx and k not in sel:
                sel[k] = {"clusterId": cl.get("id"), "role": role}
    return sel


def pull_top10(c, report, rid, clusters, kws, per_cluster):
    """One include pass, stopped once every selected keyword is found; keeps only the selected entries."""
    sel = select_top10(clusters, kws, per_cluster)
    order = [norm_kw(k.get("keyword")) for k in kws]
    pages_needed = max((order.index(k) // 200 + 1 for k in sel), default=0)
    lookups = sum(order.index(k) // 200 + 1 for k in sel)  # cost of one `keyword` lookup per selected keyword
    todo, kept, got, before = set(sel), {}, 0, c.calls
    page = 1
    while todo:
        data = c.get(f"/aio-reports/{report}/runs/{rid}/keywords", {"page": page, "itemsPerPage": 200, "include": "topOrganicResults"})
        got += len(json.dumps(data))
        rows = data.get("keywords") or []
        for k in rows:
            n = norm_kw(k.get("keyword"))
            if n in todo:
                kept[n] = {"keyword": k.get("keyword"), **sel[n], "topOrganicResults": k.get("topOrganicResults") or []}
                todo.discard(n)
        if not rows or page * 200 >= data.get("total", 0):
            break
        page += 1
    log = {"selected": len(sel), "perCluster": per_cluster, "calls": c.calls - before, "callsWithKeywordLookups": lookups, "pagesNeeded": pages_needed,
           "bytesReceived": got, "bytesKept": len(json.dumps(kept)), "missing": len(todo)}
    print(f"Top 10: {len(kept)} keywords (main + up to {per_cluster - 1} AIO keywords per cluster), {log['calls']} calls "
          f"(keyword lookups would take {lookups}), kept {log['bytesKept']:,} of {got:,} bytes.", file=sys.stderr)
    return {"rule": f"main keyword + up to {per_cluster - 1} highest-volume keywords with an AI Overview, per cluster", "log": log, "keywords": kept}


def cmd_details(c, a):
    if a.plan:
        prios = {p.strip() for p in a.priorities.split(",")}
        rows = [r for r in load_json(a.plan, {}).get("rows", []) if r.get("priority") in prios and r.get("action") in ("CREATE", "REFRESH", "CONSOLIDATE")]
        ids = list(dict.fromkeys(r["clusterId"] for r in rows))[:a.max]
    else:
        ids = [x.strip() for x in (a.clusters or "").split(",") if x.strip()]
    for cid in ids:
        dest = os.path.join(a.snapshot, "clusters", f"{cid}.json")
        if a.mixed_serp_only and os.path.exists(dest):
            continue
        detail = c.get(f"/topic-clusters/{a.project}/clusters/{cid}")
        for r in ((detail.get("mixedSerp") or {}).get("result") or []):
            for f in HEAVY_FIELDS:
                r.pop(f, None)
        if a.mixed_serp_only:
            write(dest, {"detail": detail})
            continue
        paa = c.get(f"/topic-clusters/{a.project}/clusters/{cid}/paa")
        rel = c.get(f"/topic-clusters/{a.project}/clusters/{cid}/related-searches")
        write(dest, {"detail": detail, "paa": paa.get("paa", []), "relatedSearches": rel.get("relatedSearches", [])})
    print(f"Fetched details for {len(ids)} cluster(s) into {os.path.join(a.snapshot, 'clusters')} ({c.calls} API calls)")


def norm_kw(k):
    return re.sub(r"\s+", " ", (k or "").strip().lower())


def ai_text(ov):
    """AI Overview content blocks flattened to plain lines."""
    out = []
    for b in (ov or {}).get("content") or []:
        if b.get("text"):
            out.append(("## " if b.get("type") == "header" else "") + b["text"])
        for it in b.get("list") or []:
            out.append("- " + " ".join(x for x in (it.get("header"), it.get("text")) if x))
    return out


def keyword_view(k, run, origin):
    ov = k.get("aiOverview") or {}
    return {"keyword": k.get("keyword"), "run": run, "from": origin, "volume": k.get("volume"), "hasAIO": k.get("hasAIO"),
            "brands": k.get("brands") or [], "themes": k.get("themes") or [], "brandPosition": k.get("brandPosition"),
            "ownDomainAioSource": k.get("ownDomainAioSource"), "ownDomainOrganicResult": k.get("ownDomainOrganicResult"),
            "aiText": ai_text(ov),
            "sources": [{x: s.get(x) for x in ("position", "domain", "url", "title", "organic_position")} for s in ov.get("sources") or []],
            "topOrganicResults": k.get("topOrganicResults")}


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_keyword(c, a):
    want = norm_kw(a.keyword)
    seen = []
    if a.snapshot and not a.fresh:
        man = json.load(open(os.path.join(a.snapshot, "manifest.json"))) if os.path.exists(os.path.join(a.snapshot, "manifest.json")) else {}
        path = os.path.join(a.snapshot, "aio_keywords_latest.json")
        if man.get("reportId") == a.report and os.path.exists(path):
            snap = json.load(open(path, encoding="utf-8"))
            if not a.result or (snap.get("run") or {}).get("resultId") == a.result:
                top10 = (load_json(os.path.join(a.snapshot, "aio_top10_latest.json"), {}).get("keywords") or {}).get(want)
                for k in snap.get("keywords") or []:
                    seen.append(k.get("keyword"))
                    if top10 and norm_kw(k.get("keyword")) == want:
                        k = {**k, "topOrganicResults": top10["topOrganicResults"]}
                    # Use the snapshot only when it already holds the AI Overview and the top 10.
                    if norm_kw(k.get("keyword")) == want and "topOrganicResults" in k and ("aiOverview" in k or not k.get("hasAIO")):
                        print(json.dumps(keyword_view(k, snap.get("run"), f"snapshot {a.snapshot} (0 API calls)"), ensure_ascii=False, indent=1))
                        return
    path = f"/aio-reports/{a.report}/runs/{a.result}/keywords" if a.result else f"/aio-reports/{a.report}/keywords"
    page, run = 1, None
    while True:
        data = c.get(path, {"page": page, "itemsPerPage": 200, "include": KW_INCLUDE})
        run = run or data.get("run")
        rows = data.get("keywords") or []
        for k in rows:
            seen.append(k.get("keyword"))
            if norm_kw(k.get("keyword")) == want:
                print(json.dumps(keyword_view(k, run, f"API ({c.calls} calls)"), ensure_ascii=False, indent=1))
                return
        if not rows or page * 200 >= data.get("total", 0):
            break
        page += 1
    close = difflib.get_close_matches(want, list(dict.fromkeys(norm_kw(x) for x in seen)), n=5, cutoff=0.6)
    close += [x for x in dict.fromkeys(norm_kw(x) for x in seen) if want in x and x not in close][:5 - len(close)]
    print(f"No keyword '{a.keyword}' in report {a.report} (run {(run or {}).get('resultId')}, {len(set(seen))} keywords checked, {c.calls} API calls).")
    if close:
        print("Close matches: " + "; ".join(close))
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    lp = sub.add_parser("list")
    lp.add_argument("--all", action="store_true", help="also show projects with no domain or not Done, and reports with no run")
    s = sub.add_parser("snapshot")
    s.add_argument("--project", required=True)
    s.add_argument("--report", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--as-of", help="AIO run (resultId) to treat as the current run; default the newest completed run")
    s.add_argument("--gap-days", type=int, default=0, help="previous run must be at least this many days older (28 = monthly on a daily report)")
    s.add_argument("--no-previous", action="store_true", help="do not pull a previous run")
    s.add_argument("--domains-max", type=int, default=200)
    s.add_argument("--top10-per-cluster", type=int, default=3, help="keywords per cluster whose top 10 is kept (0 = none); content-strategy thresholds top10_per_cluster")
    d = sub.add_parser("details")
    d.add_argument("--project", required=True)
    d.add_argument("--snapshot", required=True)
    d.add_argument("--clusters", help="comma-separated cluster ids")
    d.add_argument("--plan", help="plan.json: the clusters of its work rows in --priorities, up to --max")
    d.add_argument("--priorities", default="P1,P2")
    d.add_argument("--max", type=int, default=15)
    d.add_argument("--mixed-serp-only", action="store_true", help="1 call per cluster (no PAA, no related searches); skips clusters already on disk")
    k = sub.add_parser("keyword")
    k.add_argument("keyword")
    k.add_argument("--report", required=True)
    k.add_argument("--result", help="AIO run resultId; default the latest completed run")
    k.add_argument("--snapshot", help="snapshot folder to read first (0 calls when it has the keyword with top organic results)")
    k.add_argument("--fresh", action="store_true", help="skip the snapshot and call the API")
    a = ap.parse_args()
    c = Client()
    try:
        {"check": cmd_check, "list": cmd_list, "snapshot": cmd_snapshot, "details": cmd_details, "keyword": cmd_keyword}[a.cmd](c, a)
    except ApiError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
