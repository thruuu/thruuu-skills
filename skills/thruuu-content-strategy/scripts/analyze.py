#!/usr/bin/env python3
"""Turn a thruuu snapshot (Topic Clusters + AIO Monitoring) into a scored content plan.

Offline: reads the files written by thruuu-data-pull `pull.py snapshot`. No API calls.

  python3 analyze.py --snapshot DIR --profile profile.json [--thresholds thresholds.json] [--out plan.json]
  python3 analyze.py --snapshot DIR --no-profile ...      (explicit opt-out; every row gets default value)
  python3 analyze.py ... --review RUN/review.json          (applies the site-check verdicts in review.json `siteCheck`)

Output: plan.json with summary, AI Overview visibility, rows (pages to create, refresh or
consolidate, competitor pages, route-to-owner pages, protect list), skipped clusters with the rule
that skipped them, and per-cluster signals. Every number in the report comes from this file.
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
STOP = set("a an and are as at be best by can do does for from how i in is it of on or the to vs what when which who why with you your".split())
URL_NOISE = {"blog", "hc", "en", "us", "en-us", "articles", "article", "www", "html", "php", "post", "posts"}
QUESTION_START = ("what", "how", "why", "which", "who", "when", "where", "is", "are", "can", "do", "does", "should", "will")


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def norm_kw(k):
    return re.sub(r"\s+", " ", (k or "").strip().lower())


def nb(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def norm_host(h):
    h = (h or "").lower().strip()
    h = re.sub(r"^https?://", "", h).split("/")[0]
    return h[4:] if h.startswith("www.") else h


def norm_url(u):
    if not u:
        return None
    p = urlparse(u.strip())
    path = p.path.rstrip("/") or "/"
    return f"{norm_host(p.netloc)}{path}".lower()


def parse_date(s):
    try:
        return dt.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def stem(t):
    t = re.sub(r"[^a-z0-9]", "", t.lower())
    if len(t) > 4 and t.endswith("ing"):
        t = t[:-3]
    elif len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        t = t[:-1]
    return t


def tokens(text):
    return {stem(t) for t in re.split(r"[^A-Za-z0-9]+", text or "") if t and t.lower() not in STOP and stem(t)}


def is_question(k):
    k = norm_kw(k)
    return k.endswith("?") or k.split(" ")[0] in QUESTION_START


def head_shaped(k):
    """Short, non-question phrase: looks like a head term, never folded into an unrelated page."""
    return len(norm_kw(k).split()) <= 3 and not is_question(k)


def page_type(url, own_host):
    p = urlparse(url)
    h = norm_host(p.netloc)
    path = p.path.lower().rstrip("/")
    if h != own_host and h.endswith("." + own_host) and h.split(".")[0] in ("help", "support", "docs", "developers", "community"):
        return "help"
    if re.search(r"/(hc|docs|support|help|kb|knowledge-base)(/|$)", path):
        return "help"
    if path == "":
        return "home"
    if re.search(r"/(category|tag|tags|author|page)/", path + "/"):
        return "archive"
    if re.search(r"/(blog|glossary|guide|guides|learn|resources|articles|academy|insights|news|library|templates)(/|$)", path):
        return "editorial"
    return "product"


def slug_overlap(url, kw_tokens):
    parts = [s for s in urlparse(url).path.lower().split("/") if s and s not in URL_NOISE]
    if not parts:
        return None
    slug = set()
    for s in parts[-2:]:
        slug |= {stem(t) for t in re.split(r"[^a-z0-9]+", s) if t and not t.isdigit() and t not in STOP and stem(t)}
    if not slug:
        return None
    hit = sum(1 for s in slug if s in kw_tokens or any(len(x) >= 5 and len(s) >= 5 and (x.startswith(s) or s.startswith(x)) for x in kw_tokens))
    return round(hit / len(slug), 2)


def bucket(value, buckets):
    for floor, score in buckets:
        if value >= floor:
            return score
    return buckets[-1][1]


def fmt_n(n):
    return f"{int(n):,}" if n is not None else "unknown"


def pl(n, word, plural=None):
    return f"{n} {word if n == 1 else (plural or word + 's')}"


def validate_site_verdicts(verdicts, cache, cluster_ids):
    """review.json siteCheck: {clusterId: {verdict, url, method, note}}. A URL must be one the site check recorded."""
    cands = defaultdict(dict)
    for e in (cache.get("entries") or {}).values():
        for m in ("websearch", "sitemap"):
            for c in ((e.get(m) or {}).get("candidates") or []):
                cands[e.get("clusterId")].setdefault(norm_url(c["url"]), {})[m] = (e.get(m) or {}).get("checkedAt")
    out, errors = {}, []
    for cid, v in verdicts.items():
        if cid.startswith("_"):
            continue
        verdict = v.get("verdict")
        if cid not in cluster_ids:
            errors.append(f"siteCheck: unknown cluster id {cid}")
        elif verdict not in ("existing", "owner", "related", "none"):
            errors.append(f"siteCheck {cid}: verdict must be existing, owner, related or none")
        elif verdict != "none":
            if not v.get("url") or not v.get("note"):
                errors.append(f"siteCheck {cid}: verdict {verdict} needs a url and a note")
            elif norm_url(v["url"]) not in cands[cid]:
                errors.append(f"siteCheck {cid}: {v['url']} is not a candidate recorded by site_check.py for this cluster")
            else:
                found = cands[cid][norm_url(v["url"])]
                m = v.get("method") if v.get("method") in found else next(iter(found))
                out[cid] = {**v, "method": m, "checkedAt": found[m]}
        else:
            out[cid] = v
    if errors:
        sys.exit("\n".join(errors))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--profile")
    ap.add_argument("--no-profile", action="store_true", help="explicitly run without a business profile")
    ap.add_argument("--thresholds", default=os.path.join(HERE, "thresholds.json"))
    ap.add_argument("--out")
    ap.add_argument("--review", help="review.json; only its siteCheck verdicts are read here")
    a = ap.parse_args()
    if not a.profile and not a.no_profile:
        sys.exit("A business profile is required. Run profile_init.py, ask the interview questions, save profile.json, "
                 "then pass --profile. Use --no-profile only if the user explicitly declines.")
    T = load(a.thresholds)
    snap = a.snapshot
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(snap.rstrip("/"))), "plan.json")
    profile = load(a.profile, {}) if a.profile else {}
    if a.profile and not profile:
        sys.exit(f"Profile {a.profile} not found or empty.")

    project = load(os.path.join(snap, "tc_project.json"))
    clusters = load(os.path.join(snap, "tc_clusters.json"), [])
    domains = load(os.path.join(snap, "tc_domains.json"), [])
    report = load(os.path.join(snap, "aio_report.json"), {}) or {}
    latest = load(os.path.join(snap, "aio_keywords_latest.json"), {"keywords": []})
    previous = load(os.path.join(snap, "aio_keywords_previous_1.json"))
    manifest = load(os.path.join(snap, "manifest.json"), {})
    if project is None or not clusters:
        sys.exit(f"No Topic Cluster data in {snap}. Run thruuu-data-pull `pull.py snapshot` first.")

    rep = report.get("report") or {}
    own_host = norm_host(project.get("domain") or profile.get("domain") or rep.get("domain"))
    report_is_own = norm_host(rep.get("domain")) == own_host
    own_names = {nb(b) for b in list(profile.get("brandNames", [])) + ([rep.get("brandName")] if report_is_own else []) if b}
    if not own_names:
        own_names = {nb(own_host.split(".")[0])}
    notes = [w for w in manifest.get("warnings", []) if "baseline" not in w]
    if not profile:
        notes.append("No business profile: every row has business value 2 and no competitor list, so the AI Overview boost is off.")

    # Site check: verdicts from review.json, validated against the candidates site_check.py recorded.
    site_cache = load(os.path.join(snap, "site_check.json"), {}) or {}
    site_verdicts = validate_site_verdicts((load(a.review, {}) or {}).get("siteCheck") or {}, site_cache, {c.get("id") for c in clusters})

    # Competitors: only the ones the user confirmed in the profile.
    comp_alias = {}
    comp_domain = {}
    for cpt in profile.get("competitors", []):
        name = cpt.get("name")
        if not name:
            continue
        for al in [name] + list(cpt.get("aliases", [])):
            if nb(al):
                comp_alias[nb(al)] = name
        if cpt.get("domain"):
            comp_domain[norm_host(cpt["domain"])] = name
    comp_order = sorted(comp_alias, key=len, reverse=True)

    def comp_of_brand(b):
        k = nb(b)
        if k in comp_alias:
            return comp_alias[k]
        for al in comp_order:
            if len(al) >= 4 and k.startswith(al):
                return comp_alias[al]
        return None

    def comps_in_text(text):
        """Confirmed competitors named in a keyword, in order of appearance."""
        t = norm_kw(text)
        found = []
        for al, name in comp_alias.items():
            m = re.search(r"(?<![a-z0-9])" + re.escape(al) + r"(?![a-z0-9])", re.sub(r"[^a-z0-9 ]", "", t)) or (len(al) >= 6 and al in nb(t))
            if m and name not in [n for _, n in found]:
                pos = nb(t).find(al)
                found.append((pos if pos >= 0 else 999, name))
        return [n for _, n in sorted(found)]

    def domain_owner(d):
        d = norm_host(d)
        if d == own_host or d.endswith("." + own_host):
            return "own"
        for cd, name in comp_domain.items():
            if d == cd or d.endswith("." + cd):
                return name
        return None

    # Dates: freshest source wins; AIO wins ties within a day because it is the one that re-runs.
    aio_date = parse_date(((latest or {}).get("run") or {}).get("date"))
    tc_date = parse_date(project.get("createdAt"))
    aio_fresher = bool(report_is_own and aio_date and (not tc_date or aio_date >= tc_date - dt.timedelta(days=1)))
    stale_tc = bool(aio_date and tc_date and (aio_date - tc_date).days > T["stale_tc_days"])
    aio_label = f"AIO report, {aio_date.date().isoformat()}" if aio_date else "AIO report"
    tc_label = f"Topic Clusters, {tc_date.date().isoformat()}" if tc_date else "Topic Clusters"
    if not report_is_own and latest.get("keywords") and not any("tracks" in n for n in notes):
        notes.append(f"The AIO report tracks {rep.get('brandName')}; your mentions and citations are read from each AI Overview's brand list and sources, and organic positions come from Topic Clusters ({tc_label}).")

    # Own PageRank: project value, else own row in /domains.
    own_pr = project.get("pageRank") or None
    if not own_pr:
        row = next((d for d in domains if norm_host(d.get("hostname")) == own_host), None)
        if row and row.get("pageRank"):
            own_pr = row["pageRank"]
            notes.append(f"Project pageRank is {project.get('pageRank')}; used {own_host} PageRank {own_pr} from the domains list.")

    # ---------- AIO keyword rows ----------
    def index_kws(rows):
        idx = {}
        for r in rows or []:
            k = norm_kw(r.get("keyword"))
            if k in idx and (idx[k].get("volume") or 0) >= (r.get("volume") or 0):
                continue
            idx[k] = r
        return idx

    kw_now = index_kws(latest.get("keywords"))
    kw_prev = index_kws(previous.get("keywords")) if previous else {}

    # Volume floor: the minimum value, when it holds a large share of keywords, means "unknown".
    # Detected on the project's own volumes first (the backbone), then on the AIO keyword volumes.
    vols = [c.get("mainKwVolume") for c in clusters if c.get("mainKwVolume") is not None] or [r.get("volume") for r in kw_now.values() if r.get("volume") is not None]
    floor = None
    if vols:
        m = min(vols)
        if vols.count(m) / len(vols) >= T["volume_floor_min_share"]:
            floor = m

    def vol_known(v):
        return v is not None and (floor is None or v > floor)

    def kw_signals(r):
        org = (r.get("ownDomainOrganicResult") or None) if report_is_own else None
        ov = r.get("aiOverview") or {}
        srcs = ov.get("sources") or []
        brands = r.get("brands") or []
        mentioned = any(nb(b) in own_names for b in brands) or (report_is_own and r.get("brandPosition") is not None)
        own_src = next((s for s in srcs if domain_owner(s.get("domain") or s.get("url")) == "own"), None)
        cited = bool(own_src) or (report_is_own and bool(r.get("ownDomainAioSource")))
        in_query = set(comps_in_text(r.get("keyword")))
        named = []
        for b in brands:
            cn = comp_of_brand(b)
            if cn and cn not in in_query and cn not in named:
                named.append(cn)
        comp_cited = sorted({domain_owner(s.get("domain") or s.get("url")) for s in srcs} - {None, "own"})
        brand_comps = sorted({comp_of_brand(b) for b in brands} - {None})
        v = r.get("volume")
        return {
            "keyword": r.get("keyword"), "volume": v if vol_known(v) else None, "hasAIO": bool(r.get("hasAIO")),
            "mentioned": bool(r.get("hasAIO") and mentioned), "cited": bool(r.get("hasAIO") and cited),
            "organicPos": org.get("position") if org else None, "organicUrl": org.get("url") if org else None,
            "competitorsNamed": named, "competitorsInQuery": sorted(in_query), "competitorsCited": comp_cited, "brandComps": brand_comps,
            "sources": [(norm_host(s.get("domain") or s.get("url")), s.get("url")) for s in srcs],
            "themes": r.get("themes") or [],
        }

    listicle_re = re.compile(r"\b(best|top)\b|^\s*(the\s+)?\d+\s", re.I)
    top10_file = load(os.path.join(snap, "aio_top10_latest.json"), {}) or {}
    top10_map = top10_file.get("keywords") if (top10_file.get("run") or {}).get("resultId") == ((latest or {}).get("run") or {}).get("resultId") else {}
    top10_map = top10_map or {}

    def top10_signal(kw, role):
        """Compact, deterministic read of one keyword's own top 10 (AIO report), or None when it was not pulled."""
        e = top10_map.get(norm_kw(kw))
        if not e:
            return None
        pages = [t for t in e.get("topOrganicResults") or [] if t.get("serp_type") == "page" and t.get("url")]
        own = next((t for t in pages if domain_owner(t.get("domain") or t["url"]) == "own"), None)
        sg = sig_now.get(norm_kw(kw)) or {}
        return {"keyword": kw, "role": role, "pages": len(pages), "hasAIO": bool(sg.get("hasAIO")),
                "listicleTitles": sum(1 for t in pages if listicle_re.search(t.get("title") or "")),
                "community": sum(1 for t in pages if norm_host(t.get("domain")) in T["ugc_domains"]),
                "blocks": list(dict.fromkeys(t.get("serp_type") for t in e.get("topOrganicResults") or [] if t.get("serp_type") != "page")),
                "aiCites": [norm_host(t.get("domain")) for t in sorted((t for t in pages if t.get("aio_position") is not None), key=lambda t: t["aio_position"])][:3],
                "own": {"position": own["position"], "url": own["url"], "aioPosition": own.get("aio_position")} if own else None,
                "ownNotCited": bool(own and sg.get("hasAIO") and not sg.get("cited"))}

    def content_guide(c):
        """Evidence to guide the article (format, brands, themes, SERP features); never an outline. Cap: main + top10_per_cluster - 1 AIO keywords."""
        G = T["guide"]
        kws = [c.get("mainKw")] + sorted((k for k in c.get("similarity") or [] if norm_kw(k) != norm_kw(c.get("mainKw")) and (sig_now.get(norm_kw(k)) or {}).get("hasAIO")),
                                         key=lambda k: -(kw_now[norm_kw(k)].get("volume") or 0))
        kws = kws[:T["top10_per_cluster"]]
        top = [x for x in (top10_signal(k, "main" if i == 0 else "aio") for i, k in enumerate(kws)) if x]
        det = load(os.path.join(snap, "clusters", f"{c['id']}.json"), {}) or {}
        mixed = [x for x in ((det.get("detail") or {}).get("mixedSerp") or {}).get("result") or [] if x.get("serp_type", "page") == "page"]
        # Format: listicle share on the main keyword's own top 10, and on the cluster's Mixed SERP when it was pulled.
        head = top[0] if top and top[0]["role"] == "main" and top[0]["pages"] else None
        kw_share = head["listicleTitles"] / head["pages"] if head else None
        mx_list = sum(1 for x in mixed if listicle_re.search(x.get("serp_title") or ""))
        mx_share = mx_list / len(mixed) if mixed else None
        shares = [x for x in (kw_share, mx_share) if x is not None]
        fmt = None
        if shares:
            fmt = "listicle" if all(x >= G["listicle_share"] for x in shares) else "not_listicle" if all(x <= G["not_listicle_share"] for x in shares) else "mixed"
        # Brands the AI Overviews name on the selected keywords, in order of appearance; own position on the main keyword.
        brands, own_named = Counter(), None
        first = {}
        for i, k in enumerate(kws):
            r = kw_now.get(norm_kw(k)) or {}
            if not r.get("hasAIO"):
                continue
            for j, b in enumerate(r.get("brands") or []):
                brands[b] += 1
                first.setdefault(b, (i, j))
            if i == 0 and r.get("brands"):
                own_named = next(([j + 1, len(r["brands"])] for j, b in enumerate(r["brands"]) if nb(b) in own_names), [None, len(r["brands"])])
        brand_list = [{"brand": b, "keywords": n, "competitor": comp_of_brand(b), "own": nb(b) in own_names} for b, n in sorted(brands.items(), key=lambda x: (-x[1], first[x[0]]))][:G["brands_max"]]
        themes = []
        for k in kws:
            for t in (kw_now.get(norm_kw(k)) or {}).get("themes") or []:
                if t.lower() not in {x.lower() for x in themes}:
                    themes.append(t)
        feats = {f["feature"]: f["visibility"] for f in c.get("serpFeatures") or []}
        return {"keywords": [x["keyword"] for x in top] or kws[:1], "aioKeywords": sum(1 for k in kws if (kw_now.get(norm_kw(k)) or {}).get("hasAIO")),
                "format": {"suggestion": fmt, "keywordListicle": [head["listicleTitles"], head["pages"]] if head else None,
                           "mixedSerpListicle": [mx_list, len(mixed)] if mixed else None},
                "brands": brand_list, "ownNamedOnMain": own_named, "themes": themes[:G["themes_max"]],
                "clusterFeatures": {k: v for k, v in feats.items() if k in ("paa", "video", "forums", "aio") and v >= G["feature_min"]},
                "keywordBlocks": list(dict.fromkeys(b for x in top for b in x["blocks"] if b in ("questions", "video", "discussions & forums", "images", "ai overview"))),
                "aiCites": list(dict.fromkeys(d for x in top for d in x["aiCites"]))[:3],
                "top10": top}

    sig_now = {k: kw_signals(r) for k, r in kw_now.items()}
    sig_prev = {k: kw_signals(r) for k, r in kw_prev.items()}

    # Run-over-run events per keyword.
    events = []
    for k, s in sig_now.items():
        q = sig_prev.get(k)
        if not q:
            continue
        for name in ("hasAIO", "mentioned", "cited"):
            if s[name] != q[name]:
                label = {"hasAIO": "AIO", "mentioned": "mention", "cited": "citation"}[name]
                events.append({"keyword": s["keyword"], "event": ("gained " if s[name] else "lost ") + label, "volume": s["volume"]})
        if report_is_own and s["organicPos"] != q["organicPos"]:
            events.append({"keyword": s["keyword"], "event": "organic position", "from": q["organicPos"], "to": s["organicPos"], "volume": s["volume"]})
    lost_kws = {norm_kw(e["keyword"]) for e in events if e["event"] in ("lost mention", "lost citation")}

    # ---------- AI Overview visibility (share of voice, who the AI cites) ----------
    def sov(sigs):
        aio = [s for s in sigs.values() if s["hasAIO"]]
        n = len(aio)
        table = []
        names = ["__own__"] + [c.get("name") for c in profile.get("competitors", []) if c.get("name")]
        for name in names:
            if name == "__own__":
                named = sum(1 for s in aio if s["mentioned"])
                cited = sum(1 for s in aio if s["cited"])
                label = (profile.get("brandNames") or [rep.get("brandName") or own_host])[0]
            else:
                named = sum(1 for s in aio if name in s["brandComps"])
                cited = sum(1 for s in aio if name in s["competitorsCited"])
                label = name
            table.append({"brand": label, "own": name == "__own__", "named": named, "namedPct": round(100 * named / n) if n else 0,
                          "cited": cited, "citedPct": round(100 * cited / n) if n else 0})
        return {"aioKeywords": n, "keywords": len(sigs), "brands": table}

    def cited_domains(sigs):
        agg = defaultdict(lambda: {"keywords": 0, "whereOwnNotCited": 0, "urls": Counter()})
        for s in sigs.values():
            if not s["hasAIO"]:
                continue
            seen = set()
            for d, u in s["sources"]:
                if not d or d in seen:
                    continue
                seen.add(d)
                agg[d]["keywords"] += 1
                agg[d]["urls"][u] += 1
                if not s["cited"]:
                    agg[d]["whereOwnNotCited"] += 1
        out_rows = []
        for d, v in sorted(agg.items(), key=lambda x: -x[1]["keywords"]):
            owner = domain_owner(d)
            if owner == "own":
                cls = "own"
            elif owner:
                cls = "competitor"
            elif d in T["ugc_domains"]:
                cls = "video" if d in ("youtube.com", "tiktok.com") else "community"
            elif d in T["review_domains"]:
                cls = "review site"
            else:
                cls = "third-party"
            out_rows.append({"domain": d, "class": cls, "competitor": owner if owner not in (None, "own") else None,
                             "keywords": v["keywords"], "whereOwnNotCited": v["whereOwnNotCited"],
                             "topUrls": [u for u, _ in v["urls"].most_common(3)]})
        return out_rows

    visibility = {"now": sov(sig_now), "previous": sov(sig_prev) if sig_prev else None,
                  "citedDomains": cited_domains(sig_now)[:T["cited_domains_top"]],
                  "citedDomainsPrevious": {r["domain"]: r["keywords"] for r in cited_domains(sig_prev)} if sig_prev else None}
    offsite = []
    for d in cited_domains(sig_now):
        if d["class"] in ("video", "community", "review site", "third-party") and d["whereOwnNotCited"] >= T["offsite_min_keywords"]:
            act = {"video": "Publish or get featured in videos on these topics",
                   "community": "Answer in the threads the AI cites; keep it useful, not promotional",
                   "review site": "Complete and refresh your review profile; ask customers for reviews",
                   "third-party": "Pitch inclusion or an update in the cited articles (listicles, comparisons)"}[d["class"]]
            offsite.append({**d, "action": act})
    offsite = offsite[:T["offsite_top"]]

    # ---------- per-cluster signals ----------
    top, bands, O = T["rank_top"], T["position_bands"], T["opportunity"]
    skip_cats = {c.lower() for c in profile.get("skipCategories", [])}
    skip_words = [w.lower() for w in profile.get("skipKeywordContains", [])]
    conquest = profile.get("conquest") or {}
    df = Counter()
    for c in clusters:
        df.update(tokens(c.get("mainKw")))
    n_cl = max(1, len(clusters))
    distinctive = lambda text: {t for t in tokens(text) if df[t] / n_cl <= T["distinctive_df_max"]}  # noqa: E731

    cl_out = []
    url_best_for = defaultdict(list)
    joined = 0
    for c in clusters:
        if not c.get("id"):
            continue
        kws = c.get("similarity") or [c.get("mainKw")]
        rows = [sig_now[norm_kw(k)] for k in kws if norm_kw(k) in sig_now]
        joined += len(rows)
        feats = {f["feature"]: f["visibility"] for f in c.get("serpFeatures") or []}
        kw_tok = set()
        for k in kws:
            kw_tok |= tokens(k)
        count = c.get("count") or len(kws)
        if rows:
            known = sum(r["volume"] for r in rows if r["volume"] is not None)
        else:
            known = c.get("volume") if vol_known(c.get("mainKwVolume")) else 0
        volume = known or None

        by_url = defaultdict(lambda: {"kws": 0, "best": 999, "bestKw": None, "url": None})
        for r in rows:
            if r["organicPos"] is not None and r["organicUrl"]:
                u = by_url[norm_url(r["organicUrl"])]
                u["url"] = u["url"] or r["organicUrl"]
                if r["organicPos"] < u["best"]:
                    u["best"], u["bestKw"] = r["organicPos"], r["keyword"]
                if r["organicPos"] <= top:
                    u["kws"] += 1
        ranking_top_urls = [u for u in by_url.values() if u["best"] <= top]
        main = sig_now.get(norm_kw(c.get("mainKw")))
        flags = []

        # One position per row: the main keyword's, from the freshest source.
        tc_single = count == 1 and c.get("isRanking") and c.get("avgPosition") is not None
        tc_pos = c.get("avgPosition") if tc_single else None
        head_pos, pos_source, head_url = None, None, None
        if main is not None and report_is_own and aio_fresher:
            head_pos, pos_source, head_url = main["organicPos"], aio_label, main["organicUrl"]
            if count == 1 and bool(tc_pos is not None and tc_pos <= top) != bool(head_pos is not None and head_pos <= top):
                flags.append("SOURCES_DISAGREE")
        elif tc_single:
            head_pos, pos_source, head_url = tc_pos, tc_label, c.get("bestPageUrl")
            if main is not None and report_is_own and bool(main["organicPos"] and main["organicPos"] <= top) != bool(tc_pos <= top):
                flags.append("SOURCES_DISAGREE")
        if not c.get("isRanking") and ranking_top_urls and "SOURCES_DISAGREE" not in flags:
            flags.append("SOURCES_DISAGREE")
        if pos_source and pos_source.startswith("Topic Clusters") and stale_tc:
            flags.append("STALE_POSITION")
        guide = content_guide(c)
        top10 = {"keywords": guide["top10"]} if guide["top10"] else None
        main_serp = guide["top10"][0] if guide["top10"] and guide["top10"][0]["role"] == "main" else None
        own_top10 = (main_serp and main_serp["own"]) or (main and report_is_own and main["organicPos"] and main["organicPos"] <= bands["striking_max"])
        if (main and main["hasAIO"] and own_top10 and not main["cited"]) or any(x["ownNotCited"] for x in (top10 or {}).get("keywords", [])):
            flags.append("RANKS_NOT_CITED")

        target = None
        if head_url and head_pos is not None:
            target = head_url
        elif by_url:
            target = max(by_url.values(), key=lambda u: (u["kws"], -u["best"]))["url"]
        elif c.get("bestPageUrl"):
            target = c["bestPageUrl"]
        tc_url = c.get("bestPageUrl")
        if main is not None and main["organicUrl"] and tc_url and norm_url(main["organicUrl"]) != norm_url(tc_url):
            flags.append("SOURCE_CONFLICT")
        elif tc_url and target and norm_url(tc_url) != norm_url(target):
            flags.append("SOURCE_CONFLICT")
        tgt_ev = by_url.get(norm_url(target)) if target else None
        best_evidence = (tgt_ev["best"], tgt_ev["bestKw"]) if tgt_ev else ((c.get("avgPosition"), "cluster average, " + tc_label) if target and c.get("avgPosition") else (None, None))

        editorial_top = [u for u in ranking_top_urls if page_type(u["url"], own_host) == "editorial"]
        if len(ranking_top_urls) >= 2:
            flags.append("CANNIBALISATION")

        # AI Overview state on the main keyword only (never 10/mo variants).
        aio_head = main if (main and main["hasAIO"]) else None
        head_state = None
        if aio_head:
            if aio_head["mentioned"] and aio_head["cited"]:
                head_state = "named_and_cited"
            elif aio_head["mentioned"]:
                head_state = "named_not_cited"
            elif aio_head["cited"]:
                head_state = "cited_not_named"
            elif aio_head["competitorsNamed"]:
                head_state = "absent_competitors_named"
            else:
                head_state = "absent"
        aio_rows = [r for r in rows if r["hasAIO"]]
        lost = [r["keyword"] for r in rows if norm_kw(r["keyword"]) in lost_kws]

        ptype = page_type(target, own_host) if target else None
        overlap = slug_overlap(target, kw_tok) if target and ptype != "home" else None
        intent = c.get("intent")
        cat = c.get("category")
        mk = norm_kw(c.get("mainKw"))
        in_query = comps_in_text(c.get("mainKw"))

        action, subtype, why, skip_reason = None, None, "", None
        if c.get("hidden"):
            skip_reason = "hidden in thruuu"
        elif cat and cat.lower() in skip_cats:
            skip_reason = f"profile skipCategories: '{cat}'"
        else:
            w = next((w for w in skip_words if w in mk), None)
            if w:
                skip_reason = f"profile skipKeywordContains: '{w}'"
            elif in_query and conquest.get("include") is False:
                skip_reason = f"competitor query ({in_query[0]}); profile conquest.include is false"
        if skip_reason:
            action, subtype, why = "SKIP", "skip", skip_reason
        elif not target:
            action, subtype, why = "CREATE", "create", "no page of yours ranks for any keyword in the cluster"
        elif (ptype in ("home", "help", "archive") or (ptype == "product" and intent == "informational")) and (head_pos is None or head_pos > bands["striking_max"]):
            action, subtype, why = "CREATE", "create_dedicated", f"only a {ptype} page ranks and it cannot be reshaped for this cluster"
        elif overlap is not None and overlap < T["off_topic_overlap"] and (head_pos is None or head_pos > bands["striking_max"]):
            action, subtype, why = "CREATE", "create_dedicated", f"the ranking page is about another topic (slug overlap {overlap})"
            flags.append("OFF_TOPIC_PAGE")
        elif head_pos is None:
            bp = best_evidence[0]
            action = "REFRESH"
            subtype = "expand" if bp is not None and bp <= bands["striking_max"] else "expand_weak" if bp is not None and bp <= T["expand_mid_max"] else "expand_thin"
            why = "page ranks for other keywords of the cluster but not the main keyword"
        elif head_pos <= bands["protect_max"]:
            if head_state in ("absent_competitors_named",):
                action, subtype, why = "REFRESH", "aio_citation", "top 3 organically but absent from the AI Overview while competitors are named"
            elif head_state in ("cited_not_named",):
                action, subtype, why = "REFRESH", "brand_anchor", "cited in the AI Overview but the brand is not named"
            elif head_state in ("named_not_cited",):
                action, subtype, why = "REFRESH", "win_citation", "named in the AI Overview but another page is cited"
            else:
                action, subtype, why = "MONITOR", "protect", "top 3 and no AI Overview gap"
        elif head_pos <= bands["striking_max"]:
            action, subtype, why = "REFRESH", "striking", "positions 4 to 10"
        elif head_pos <= bands["page_two_max"]:
            action, subtype, why = "REFRESH", "page_two", "positions 11 to 20"
        elif head_pos <= bands["rewrite_max"]:
            action, subtype, why = "REFRESH", "rewrite", "positions 21 to 50"
        else:
            action, subtype, why = "CREATE", "create", "best position beyond 50"
        # Site check: an existing page thruuu cannot see (outside its top 20) turns a CREATE into a REFRESH.
        site = None
        sv = site_verdicts.get(c["id"])
        if sv and action == "CREATE" and sv["verdict"] in ("existing", "owner", "related"):
            stype = page_type(sv["url"], own_host)
            owner_like = stype in ("home", "help", "archive") or (stype == "product" and intent == "informational") or "/pric" in urlparse(sv["url"]).path.lower()
            verdict = "owner" if sv["verdict"] == "existing" and owner_like else sv["verdict"]
            site = {"verdict": verdict, "url": sv["url"], "method": sv["method"], "checkedAt": sv.get("checkedAt"), "note": sv.get("note"), "pageType": stype}
            if verdict == "existing":
                action, subtype, why = "REFRESH", "existing_unranked", f"existing page found by {'site search' if sv['method'] == 'websearch' else 'sitemap'}, outside thruuu's top 20"
                target, ptype = sv["url"], stype
                pos_source = f"outside thruuu's top 20 (checked {sv.get('checkedAt') or 'this run'})"
                flags.append("FOUND_BY_SITE_SEARCH" if sv["method"] == "websearch" else "FOUND_IN_SITEMAP")
            elif verdict == "owner":
                action, subtype, why = "CREATE", "create_dedicated", f"the site has only a {stype} page on this topic"
                target, ptype = sv["url"], stype
                flags.append("OWNER_PAGE_FOUND")
            else:
                flags.append("RELATED_PAGE_FOUND")
        weak_page = action in ("REFRESH", "MONITOR") and (ptype in ("home", "help", "archive") or (ptype == "product" and intent == "informational"))
        if weak_page:
            flags.append("WEAK_PAGE_TYPE")
        if action == "CREATE" and subtype != "create_dedicated":
            target = None

        # SERP shape with the SERP count, never a bare percentage.
        fmt = []
        for f, key in (("video", "video"), ("forums", "forums")):
            v = feats.get(key, 0)
            k = round(v * count / 100)
            if v >= T["format"][f + "_min"] and count >= T["format"]["min_serps"]:
                fmt.append(f"{key} on {k} of {count} SERPs")

        if tc_url:
            url_best_for[norm_url(tc_url)].append(c["id"])

        cl_out.append({
            "id": c["id"], "mainKw": c.get("mainKw"), "category": cat, "intent": intent, "count": count,
            "volume": volume, "volumeKnown": volume is not None, "tcVolume": c.get("volume"),
            "averagePR": c.get("averagePR"), "serp": feats, "top10": top10, "guide": guide, "themes": main["themes"] if main else [], "briefId": c.get("briefId"), "scraped": c.get("scraped"),
            "tc": {"isRanking": c.get("isRanking"), "avgPosition": c.get("avgPosition"), "bestPageUrl": tc_url},
            "keywordsJoined": len(rows), "keywords": kws,
            "headPos": head_pos, "posSource": pos_source, "target": target, "targetType": ptype, "slugOverlap": overlap,
            "bestEvidence": {"position": best_evidence[0], "keyword": best_evidence[1]},
            "ownUrls": sorted(({"url": u["url"], "bestPos": u["best"], "bestKw": u["bestKw"], "kwsTop20": u["kws"]} for u in by_url.values()), key=lambda x: x["bestPos"]),
            "editorialTop": [u["url"] for u in sorted(editorial_top, key=lambda u: u["best"])],
            "headShaped": head_shaped(c.get("mainKw")), "question": is_question(c.get("mainKw")),
            "distinctive": sorted(distinctive(c.get("mainKw"))), "competitorsInQuery": in_query,
            "aio": {"head": head_state, "headKeyword": c.get("mainKw") if aio_head else None,
                    "headCompetitors": aio_head["competitorsNamed"] if aio_head else [],
                    "keywords": len(aio_rows), "mentioned": sum(r["mentioned"] for r in aio_rows), "cited": sum(r["cited"] for r in aio_rows),
                    "lostKeywords": lost},
            "kwStates": {r["keyword"]: {"pos": r["organicPos"], "hasAIO": r["hasAIO"], "mentioned": r["mentioned"], "cited": r["cited"]} for r in rows},
            "action": action, "subtype": subtype, "why": why, "skipReason": skip_reason, "flags": flags, "format": fmt, "site": site,
        })

    for c in cl_out:
        if c["tc"]["bestPageUrl"] and len(url_best_for[norm_url(c["tc"]["bestPageUrl"])]) > 1:
            c["flags"].append("SHARED_PAGE")
    by_id = {c["id"]: c for c in cl_out}

    # ---------- rows ----------
    rows, protect, skipped = [], [], []
    url_groups, owner_groups, comp_groups = {}, {}, defaultdict(list)
    create_pool = []

    def new_row(key, kind, action, primary, members):
        return {"key": key, "kind": kind, "action": action, "primary": primary["id"], "clusters": [m["id"] for m in members], "attached": [], "protect": []}

    for c in sorted(cl_out, key=lambda x: -(x["volume"] or 0)):
        if c["action"] == "SKIP":
            skipped.append({"clusterId": c["id"], "mainKw": c["mainKw"], "reason": c["skipReason"]})
            continue
        if c["competitorsInQuery"] and comp_alias:
            if re.search(T["comparison_pattern"], norm_kw(c["mainKw"])) or len(c["competitorsInQuery"]) >= 2:
                comp_groups[tuple(c["competitorsInQuery"])].append(c)
                continue
            if not conquest.get("navigational", False) and c["action"] != "MONITOR":
                c["skipReason"] = f"about {c['competitorsInQuery'][0]} itself, not a comparison (profile conquest.navigational is off)"
                skipped.append({"clusterId": c["id"], "mainKw": c["mainKw"], "reason": c["skipReason"]})
                continue
        if c["action"] in ("REFRESH", "MONITOR"):
            k = "url:" + norm_url(c["target"])
            (owner_groups if "WEAK_PAGE_TYPE" in c["flags"] else url_groups).setdefault(k, []).append(c)
            continue
        create_pool.append(c)

    def build_url_row(k, members, kind):
        work = [m for m in members if m["action"] == "REFRESH"]
        if not work:
            protect.append({"key": k, "clusters": [m["id"] for m in members]})
            return None
        primary = max(work, key=lambda m: ((m["volume"] or 0), m["headPos"] is not None))
        r = new_row(k, kind, "ROUTE" if kind == "owner" else "REFRESH", primary, work)
        r["primary"] = primary["id"]
        r["protect"] = [m["id"] for m in members if m["action"] == "MONITOR"]
        if kind == "editorial":
            others = [u for m in work for u in m["editorialTop"] if norm_url(u) != k[4:]]
            others = [u for u in dict.fromkeys(others) if "url:" + norm_url(u) not in url_groups]
            if others:
                r["action"] = "CONSOLIDATE"
                r["consolidateFrom"] = others
        return r

    for k, members in url_groups.items():
        r = build_url_row(k, members, "editorial")
        if r:
            rows.append(r)
    owner_rows = []
    for k, members in owner_groups.items():
        r = build_url_row(k, members, "owner")
        if r:
            owner_rows.append(r)

    # One row per competitor: a multi-competitor query joins the competitor with the most queries.
    comp_count = Counter(n for key, ms in comp_groups.items() for n in key for _ in ms)
    regrouped = defaultdict(list)
    for key, ms in comp_groups.items():
        regrouped[max(key, key=lambda n: (comp_count[n], -key.index(n)))].extend(ms)
    for name, members in regrouped.items():
        refresh = [m for m in members if m["action"] == "REFRESH" and "WEAK_PAGE_TYPE" not in m["flags"]]
        work = [m for m in members if m["action"] in ("REFRESH", "CREATE")]
        if not work:
            protect.append({"key": "competitor:" + nb(name), "clusters": [m["id"] for m in members]})
            continue
        primary = max(refresh or work, key=lambda m: (m["volume"] or 0))
        r = new_row("competitor:" + nb(name), "competitor", "REFRESH" if refresh else "CREATE", primary, work)
        r["competitor"] = name
        r["protect"] = [m["id"] for m in members if m["action"] == "MONITOR"]
        rows.append(r)

    # CREATE pool: fold into a same-category refresh page, else merge by category into one hub page.
    def can_join(host_cluster, c):
        if set(c["distinctive"]) & set(host_cluster["distinctive"]):
            return True
        return not c["headShaped"]

    refresh_hosts = defaultdict(list)
    for r in rows:
        if r["kind"] == "editorial":
            for i in r["clusters"]:
                if by_id[i]["category"]:
                    refresh_hosts[by_id[i]["category"]].append(r)
    remaining = []
    for c in create_pool:
        hosts = [r for r in refresh_hosts.get(c["category"], []) if can_join(by_id[r["primary"]], c)] if c["category"] and c["category"].lower() not in ("uncategorized", "unknown") else []
        small = not c["volumeKnown"] or c["volume"] < T["min_article_volume"]
        if hosts and small:
            max(hosts, key=lambda r: by_id[r["primary"]]["volume"] or 0)["attached"].append(c["id"])
        else:
            remaining.append(c)
    parked = []
    by_cat = defaultdict(list)
    for c in remaining:
        cat = c["category"]
        if not cat or cat.lower() in ("uncategorized", "unknown"):
            if c["volumeKnown"] and c["volume"] >= T["min_article_volume"]:
                rows.append(new_row("cluster:" + c["id"], "editorial", "CREATE", c, [c]))
            else:
                parked.append(c["id"])
            continue
        by_cat[cat].append(c)
    # One hub row per category. Members sharing a distinctive term with the hub, and small questions,
    # become sections of the hub; other clusters with demand are listed as supporting pages, not merged.
    for cat, members in by_cat.items():
        pool = sorted(members, key=lambda m: (-(m["volume"] or 0), not m["headShaped"], -(m["count"] or 0)))
        hub = pool.pop(0)
        merged, supporting = [], []
        for m in pool:
            small = not m["volumeKnown"] or m["volume"] < T["min_article_volume"]
            if set(m["distinctive"]) & set(hub["distinctive"]) or (small and not m["headShaped"]):
                merged.append(m)
            else:
                supporting.append(m)
        r = new_row("cluster:" + hub["id"], "editorial", "CREATE", hub, [hub] + merged)
        r["category"] = cat
        r["supporting"] = [m["id"] for m in supporting]
        rows.append(r)

    # Cross-category fold: a small question-shaped CREATE row joins a row with real demand on the same distinctive term.
    def small(c):
        return not c["volumeKnown"] or c["volume"] < T["min_article_volume"]
    hosts_all = [r for r in rows if r["kind"] in ("editorial", "competitor") and not small(by_id[r["primary"]])]
    keep = []
    for r in rows:
        hub = by_id[r["primary"]]
        if r["action"] == "CREATE" and r["kind"] == "editorial" and small(hub) and not hub["headShaped"] and not r.get("supporting") \
                and all(small(by_id[i]) for i in r["clusters"]):
            cands = [h for h in hosts_all if h is not r and set(hub["distinctive"]) & set(by_id[h["primary"]]["distinctive"])]
            if cands:
                host = max(cands, key=lambda h: by_id[h["primary"]]["volume"] or 0)
                host["attached"].extend(r["clusters"])
                continue
        keep.append(r)
    rows = keep

    # ---------- score ----------
    comp = T["competition"]
    am = T["aio_modifier"]
    bv_cfg = profile.get("businessValue", {})
    P = T["priority"]

    def business_value(c):
        v = bv_cfg.get("categories", {}).get(c["category"])
        if v is not None:
            return v, True
        hits = [val for w, val in bv_cfg.get("keywordContains", {}).items() if w.lower() in norm_kw(c["mainKw"])]
        if hits:
            return max(hits), True
        return bv_cfg.get("default", T["business_value_default"]), bool(profile)

    def score_row(r):
        members = [by_id[i] for i in r["clusters"]]
        attached = [by_id[i] for i in r["attached"]]
        p = by_id[r["primary"]]
        known = [m["volume"] for m in members + attached if m["volumeKnown"]]
        demand_vol = sum(known) if known else None
        demand = bucket(demand_vol, T["demand_buckets"]) if demand_vol else T["demand_unknown"]
        row_act = "CREATE" if r["action"] == "CREATE" else "REFRESH"
        heads = [m for m in members if m["volumeKnown"] and m["volume"] >= T["min_article_volume"] and m["action"] == row_act] or [p]
        opp_key = max((m["subtype"] for m in heads), key=lambda s: O.get(s, 0), default=p["subtype"])
        opp = O.get(opp_key, O["create"])
        pr = p["averagePR"]
        if own_pr and pr is not None:
            gap = pr - own_pr
            cf = max(comp["floor"], min(1.0, 1 - comp["per_point"] * max(0, gap)))
            label = "Low" if gap <= 0 else "Moderate" if gap <= comp["moderate_margin"] else "High"
        else:
            cf, label = comp["unknown"], "Unknown"
        states = [m["aio"]["head"] for m in heads if m["aio"]["head"]]
        lost = [k for m in heads for k in m["aio"]["lostKeywords"] if norm_kw(k) == norm_kw(m["mainKw"])]
        if lost:
            aio_key = "lost"
        elif "absent_competitors_named" in states:
            aio_key = "absent_competitors_named"
        elif "named_not_cited" in states:
            aio_key = "named_not_cited"
        elif "cited_not_named" in states:
            aio_key = "cited_not_named"
        else:
            aio_key = "none"
        amod = am[aio_key]
        if r["kind"] == "competitor":
            bv, bv_known = conquest.get("businessValue", 3), True
        else:
            bv, bv_known = business_value(p)
        score = round(demand * opp * cf * amod * (bv / 2), 1)
        flags = sorted({f for m in heads + [p] for f in m["flags"]})
        if r["kind"] == "owner":
            prio = "OWNER"
        elif score >= P["p1_min"] and demand_vol is not None and demand_vol >= P["p1_min_volume"]:
            prio = "P1"
        elif score >= P["p2_min"] and (demand_vol is None or demand_vol >= P["p2_min_volume"]):
            prio = "P2"
        else:
            prio = "P3"
        capped = None
        if demand_vol is None and score >= P["p1_min"]:
            capped = "capped at P2: demand unknown, size it first"
        if prio == "P1" and ("SOURCES_DISAGREE" in flags or "STALE_POSITION" in flags):
            prio, capped = "P2", "capped at P2 until the position is confirmed in Search Console"
        return {"demandVol": demand_vol, "demand": demand, "opp": opp, "oppKey": opp_key, "cf": round(cf, 2), "label": label, "pr": pr,
                "aioKey": aio_key, "amod": amod, "bv": bv, "bvKnown": bv_known, "score": score, "prio": prio, "flags": flags,
                "capped": capped, "lost": lost, "heads": [m["id"] for m in heads]}

    comp_members_named = lambda members: Counter(n for m in members for n in m["aio"]["headCompetitors"])  # noqa: E731

    def finish(r):
        s = score_row(r)
        members = [by_id[i] for i in r["clusters"]]
        p = by_id[r["primary"]]
        pos = p["headPos"]
        target = p["target"] if r["action"] in ("REFRESH", "CONSOLIDATE", "ROUTE") else None
        existing = p["target"] if p["subtype"] == "create_dedicated" else None
        comps = comp_members_named([by_id[i] for i in s["heads"]])
        parts = []
        if r["kind"] == "competitor":
            parts.append(f"{pl(len(members), 'query cluster')} naming {r['competitor']}, grouped into one comparison or alternatives page.")
        site = p.get("site")
        if r["action"] in ("REFRESH", "CONSOLIDATE", "ROUTE"):
            if site and site["verdict"] == "existing":
                how = "site search" if site["method"] == "websearch" else "the sitemap"
                parts.append(f"Existing page found by {how}: {site['url']} covers '{p['mainKw']}' but is outside thruuu's top 20. Refresh it instead of writing a second page.")
            elif pos is not None:
                parts.append(f"'{p['mainKw']}' ranks #{pos} ({p['posSource']}) with this page.")
            else:
                be = p["bestEvidence"]
                parts.append(f"'{p['mainKw']}' does not rank ({p['posSource'] or aio_label}); this page's best is #{be['position']} on '{be['keyword']}'. Retarget it.")
        elif r["action"] == "CREATE":
            if site and site["verdict"] == "owner":
                parts.append(f"New page: the site only has a {site['pageType']} page on this ({site['url']}), outside thruuu's top 20. Write the article and link to it; its owner keeps that page.")
            elif existing:
                what = ("only the homepage" if p["targetType"] == "home" else f"only a page about another topic ({existing})" if "OFF_TOPIC_PAGE" in p["flags"]
                        else f"only a {p['targetType']} page ({existing})")
                where = f", #{p['headPos']}" if p["headPos"] else ""
                parts.append(f"New page: {what} ranks today{where}; it cannot be reshaped for this topic.")
            else:
                parts.append(f"No page of yours ranks for '{p['mainKw']}'.")
        if site and site["verdict"] == "related":
            parts.append(f"Related page on the site: {site['url']} (same subject, different intent). Link the two pages both ways and keep the angles distinct.")
        if len(members) > 1 and r["kind"] != "competitor":
            parts.append(f"One page for {pl(len(members), 'cluster')}" + (f" in '{r['category']}'." if r.get("category") else "."))
        if r["attached"]:
            parts.append(f"Answer {pl(len(r['attached']), 'related question')} as sections.")
        if r.get("supporting"):
            sv = sum(by_id[i]["volume"] or 0 for i in r["supporting"])
            parts.append(f"{pl(len(r['supporting']), 'supporting page')} in the same category ({fmt_n(sv)}/mo) to plan after this hub; see plan.csv.")
        if r.get("consolidateFrom"):
            parts.append(f"Merge {', '.join(r['consolidateFrom'])} into this URL (both rank top 20 in one cluster).")
        heads = [by_id[i] for i in s["heads"] if by_id[i]["aio"]["head"]]
        if heads:
            hs = [m["aio"]["head"] for m in heads]
            if "absent_competitors_named" in hs:
                parts.append(f"AI Overview on the main keyword names {', '.join(n for n, _ in comps.most_common(3))}, not you.")
            elif "named_not_cited" in hs:
                parts.append("The AI Overview names you but cites another page: make the answer quotable on this URL.")
            elif "cited_not_named" in hs:
                parts.append("The AI Overview cites this site without naming the brand.")
            elif "named_and_cited" in hs:
                parts.append("Named and cited in the AI Overview: keep it that way.")
        if s["lost"]:
            parts.append(f"Lost the AI Overview mention or citation since last run on: {', '.join(s['lost'][:3])}.")
        if "RANKS_NOT_CITED" in p["flags"]:
            nc = [x for x in (p["top10"] or {}).get("keywords", []) if x["ownNotCited"]]
            sv = nc[0] if nc else {"keyword": p["mainKw"], "citedPages": []}
            cited = ", ".join(f"{x['domain']} (#{x['position']})" for x in sv.get("citedPages", [])[:3])
            where = f" (your page #{sv['own']['position']})" if sv.get("own") else ""
            parts.append(f"Ranks top 10 for '{sv['keyword']}'{where} but its AI Overview does not cite you" + (f"; it cites {cited} from the same results" if cited else "") + ".")
        lost_other = [k for m in members + [by_id[i] for i in r["attached"]] for k in m["aio"]["lostKeywords"] if k not in s["lost"]]
        if lost_other:
            parts.append(f"Lost the AI Overview mention or citation on {', '.join(lost_other[:3])} (a section of this page, so no priority boost).")
        if s["demandVol"] is None:
            parts.append("Demand unknown (all keywords at the volume floor); size it before briefing.")
        if "SOURCES_DISAGREE" in s["flags"]:
            parts.append("Topic Clusters and the AIO report disagree on whether this ranks; check Search Console.")
        if "STALE_POSITION" in s["flags"]:
            parts.append(f"Position comes from Topic Clusters older than {T['stale_tc_days']} days; re-cluster or check Search Console.")
        if "WEAK_PAGE_TYPE" in s["flags"]:
            parts.append(f"The ranking URL is a {p['targetType']} page: route to its owner, do not write a competing blog post.")
        if s["capped"]:
            parts.append(f"Priority {s['capped']}.")
        # Self-cannibalisation guard with the sibling's own main-keyword position.
        sib = None
        if r["action"] == "CREATE" and p["category"]:
            cands = [(c2["headPos"], c2["target"], c2["mainKw"]) for c2 in cl_out if c2["category"] == p["category"] and c2["id"] not in r["clusters"]
                     and c2["headPos"] is not None and c2["headPos"] <= bands["striking_max"] and c2["target"] and page_type(c2["target"], own_host) == "editorial"]
            if cands:
                sib = min(cands)
                s["flags"].append("CHECK_SIBLING_PAGE")
                parts.append(f"Check first: {sib[1]} ranks #{sib[0]} for '{sib[2]}' in the same category; if the intent is the same, refresh it instead.")
        tp = (3 if pos is not None and pos <= bands["striking_max"] else 10) if r["action"] in ("REFRESH", "CONSOLIDATE", "ROUTE") else 20
        if s["oppKey"] == "existing_unranked":
            tp = T["site_check"]["existing_target_pos"]
        absent_heads = [by_id[i]["mainKw"] for i in s["heads"] if by_id[i]["aio"]["head"] in ("absent", "absent_competitors_named", "named_not_cited", "cited_not_named")]
        success = {"clusterId": p["id"], "keyword": p["mainKw"], "baselinePos": pos, "targetPos": tp, "baselineUrl": existing,
                   "weeks": 8 if r["action"] != "CREATE" else 12, "aioKeywords": absent_heads}
        check = f"'{p['mainKw']}' in the top {tp} within {success['weeks']} weeks" + (f", and named or cited in the AI Overview for '{absent_heads[0]}'" if absent_heads else "")
        effort = "Low" if s["oppKey"] in ("brand_anchor", "aio_citation", "win_citation") else "High" if r["action"] == "CREATE" else "Medium"
        r.update({
            "mainKw": p["mainKw"], "category": r.get("category") or p["category"], "intent": p["intent"], "clusterId": p["id"],
            "volume": s["demandVol"], "demandKnown": s["demandVol"] is not None, "keywordCount": sum(m["count"] for m in members + [by_id[i] for i in r["attached"]]),
            "target": target, "existingWeakPage": existing, "position": pos, "posSource": p["posSource"],
            "bestEvidence": p["bestEvidence"], "subtype": s["oppKey"], "competition": s["label"], "averagePR": s["pr"],
            "aio": {"head": p["aio"]["head"], "state": s["aioKey"], "competitors": comps.most_common(5),
                    "keywordsAll": sum(m["aio"]["keywords"] for m in members), "lost": s["lost"]},
            "businessValue": s["bv"], "businessValueFromProfile": s["bvKnown"],
            "score": s["score"], "priority": s["prio"], "effort": effort, "flags": sorted(set(s["flags"])), "format": list(dict.fromkeys(f for m in members for f in m["format"])),
            "scoreBreakdown": (f"demand {s['demand']} ({fmt_n(s['demandVol'])}/mo" + (", unknown: neutral" if s["demandVol"] is None else "") + f") x opportunity {s['opp']} ({s['oppKey'].replace('_', ' ')})"
                               f" x competition {s['cf']} ({s['label']}, avg PR {s['pr']} vs yours {own_pr}) x AIO {s['amod']} ({s['aioKey'].replace('_', ' ')})"
                               f" x business value {s['bv']}/2" + ("" if s["bvKnown"] else " (default)")),
            "rationale": " ".join(parts), "success": success, "successCheck": check,
            "secondaryKeywords": [by_id[i]["mainKw"] for i in r["clusters"] if i != r["primary"]],
            "questionsToFold": [by_id[i]["mainKw"] for i in r["attached"]],
            "guide": {k: v for k, v in p["guide"].items() if k != "top10"},
            "questionsAio": [{"keyword": by_id[i]["mainKw"], "sourceDomains": list(dict.fromkeys(d for d, _ in sig_now[norm_kw(by_id[i]["mainKw"])]["sources"] if d))[:5]}
                             for i in r["attached"] if (sig_now.get(norm_kw(by_id[i]["mainKw"])) or {}).get("hasAIO")],
            "protectKeywords": [f"{by_id[i]['mainKw']} (#{by_id[i]['headPos']})" for i in r["protect"]],
            "supportingPages": [{"mainKw": by_id[i]["mainKw"], "volume": by_id[i]["volume"]} for i in r.get("supporting", [])],
            "memberClusterIds": r["clusters"] + r["attached"] + r.get("supporting", []),
            "siteCheck": site,
        })
        return r

    rows = [finish(r) for r in rows]
    owner_rows = [finish(r) for r in owner_rows]
    order = {"P1": 0, "P2": 1, "P3": 2}
    eff_rank = {"Low": 0, "Medium": 1, "High": 2}
    rows.sort(key=lambda r: (order[r["priority"]], -r["score"], eff_rank[r["effort"]], -(r["volume"] or 0)))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    owner_rows.sort(key=lambda r: -r["score"])

    # ---------- site check coverage ----------
    checked = {e.get("clusterId") for e in (site_cache.get("entries") or {}).values() if e.get("websearch") or e.get("sitemap")}
    unchecked = [r for r in rows if r["action"] == "CREATE" and r["clusterId"] not in checked]
    methods = Counter(m for e in (site_cache.get("entries") or {}).values() for m in ("websearch", "sitemap") if e.get(m))
    site_summary = {"entries": len(site_cache.get("entries") or {}), "methods": dict(methods), "verdicts": dict(Counter(v["verdict"] for v in site_verdicts.values())),
                    "converted": sum(1 for c in cl_out if c.get("site") and c["site"]["verdict"] == "existing"), "createRowsUnchecked": len(unchecked)}
    if not top10_map:
        notes.append("The snapshot has no per-keyword top 10 (aio_top10_latest.json): SERP notes use the cluster view only. Re-pull to add it.")
    if unchecked:
        notes.append(f"{len(unchecked)} CREATE rows have no site check yet (thruuu only sees the top 20): run site_check.py before briefing them.")

    # ---------- summary ----------
    st = (report.get("runs") or [{}])[0].get("stats") or {}
    summary = {
        "domain": own_host, "brand": (profile.get("brandNames") or [rep.get("brandName")])[0], "ownPageRank": own_pr,
        "project": {"id": project.get("id"), "label": project.get("label"), "createdAt": project.get("createdAt"), "searchParam": project.get("searchParam")},
        "aioReport": {"id": rep.get("id"), "label": rep.get("label"), "brand": rep.get("brandName"), "tracksOwnBrand": report_is_own,
                      "type": rep.get("type"), "frequency": (rep.get("schedule") or {}).get("frequency"),
                      "runs": [{"resultId": x.get("resultId"), "date": x.get("date")} for x in report.get("runs") or []]},
        "positionSource": aio_label if aio_fresher else tc_label,
        "pulledAt": manifest.get("pulledAt"), "runDate": (aio_date or tc_date).isoformat() if (aio_date or tc_date) else manifest.get("pulledAt"),
        "clusters": len(cl_out), "keywords": sum(len(c["keywords"]) for c in cl_out), "keywordsJoined": joined,
        "singletonClusters": sum(1 for c in cl_out if c["count"] == 1),
        "volumeFloor": floor, "clustersDemandUnknown": sum(1 for c in cl_out if not c["volumeKnown"]),
        "clustersRankingTop20": sum(1 for c in cl_out if c["headPos"] is not None and c["headPos"] <= top),
        "clustersWithAnyRankingPage": sum(1 for c in cl_out if any(u["bestPos"] <= top for u in c["ownUrls"]) or (c["headPos"] is not None and c["headPos"] <= top)),
        "clustersRankingTC": sum(1 for c in cl_out if c["tc"]["isRanking"]),
        "reportStats": {k: st.get(k) for k in ("totalKeywords", "aioKeywordCount", "aioPresence", "visibilityScore", "domainCitation")} if report_is_own else None,
        "rowsDemandUnknown": sum(1 for r in rows if not r["demandKnown"]),
        "aioEvents": events, "hasPreviousRun": bool(kw_prev), "previousRunDate": (previous or {}).get("run", {}).get("date"),
        "sharedPages": {u: [{"mainKw": by_id[i]["mainKw"], "headPos": by_id[i]["headPos"], "volume": by_id[i]["volume"]} for i in ids] for u, ids in url_best_for.items() if len(ids) > 1},
        "siteCheck": site_summary,
        "top10": {"keywordsPulled": len(top10_map), "clustersWithTop10": sum(1 for c in cl_out if c.get("top10")), "pull": top10_file.get("log")},
        "hasProfile": bool(profile), "competitors": [c.get("name") for c in profile.get("competitors", [])],
        "notes": notes,
    }
    plan = {"version": 2, "thresholds": T, "summary": summary, "visibility": visibility, "offsite": offsite,
            "rows": rows, "ownerRows": owner_rows, "protect": protect, "parked": parked, "skipped": skipped, "clusters": cl_out}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    acts = Counter(r["action"] for r in rows)
    print(f"Wrote {out}: {len(rows)} plan rows {dict(acts)}, priorities {dict(Counter(r['priority'] for r in rows))}, "
          f"{len(owner_rows)} route-to-owner, {len(protect)} protect, {len(parked)} parked, {len(skipped)} skipped clusters. "
          f"Keywords joined {joined}/{summary['keywords']}; {summary['clustersDemandUnknown']} clusters with no measured demand (floor {floor}).")
    for n in notes:
        print("NOTE:", n)


if __name__ == "__main__":
    main()
