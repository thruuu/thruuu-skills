#!/usr/bin/env python3
"""Pre-fill the business profile interview from a snapshot.

  python3 profile_init.py --snapshot DIR --out profile.draft.json

Lists every brand the AI Overviews name (with the domain most often cited for it), the
categories with cluster counts and known demand, and the questions to ask. The user confirms
competitors and values; the agent then writes profile.json. Nothing here is a decision.
"""
import argparse
import json
import os
import re
from collections import Counter, defaultdict


def load(p, d=None):
    if not os.path.exists(p):
        return d
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def nb(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def host(h):
    h = re.sub(r"^https?://", "", (h or "").lower()).split("/")[0]
    return h[4:] if h.startswith("www.") else h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    s = a.snapshot
    project = load(os.path.join(s, "tc_project.json"), {})
    clusters = load(os.path.join(s, "tc_clusters.json"), [])
    report = (load(os.path.join(s, "aio_report.json"), {}) or {}).get("report") or {}
    kws = (load(os.path.join(s, "aio_keywords_latest.json"), {}) or {}).get("keywords", [])
    own = host(project.get("domain"))
    own_names = {nb(report.get("brandName"))} if host(report.get("domain")) == own else set()
    own_names.add(nb(own.split(".")[0]))

    named = Counter()
    display = {}
    dom_for = defaultdict(Counter)
    aio_n = 0
    for r in kws:
        if not r.get("hasAIO"):
            continue
        aio_n += 1
        srcs = [host(x.get("domain") or x.get("url")) for x in ((r.get("aiOverview") or {}).get("sources") or [])]
        for b in set(r.get("brands") or []):
            k = nb(b)
            if not k or k in own_names:
                continue
            named[k] += 1
            display.setdefault(k, b)
            for d in srcs:
                if k[:5] and k[:5] in nb(d):
                    dom_for[k][d] += 1

    cats = defaultdict(lambda: {"clusters": 0, "volume": 0})
    for c in clusters:
        k = c.get("category") or "Uncategorized"
        cats[k]["clusters"] += 1
        cats[k]["volume"] += c.get("volume") or 0

    draft = {
        "_doc": "DRAFT. Confirm every field with the user, then save as profile.json. Nothing here is decided.",
        "domain": own,
        "brandNames": sorted({report.get("brandName")} - {None}) if own_names else [],
        "questions": [
            "1. What do you sell, to whom? (one sentence each: offer, audience)",
            "2. Which of the brands below are real competitors? Keep, drop, or add. Platforms like Google or Microsoft are usually not.",
            "3. Do you want pages targeting competitor queries (vs, alternatives, pricing)? include or skip",
            "4. Which categories make money (business value 3) and which are awareness only (1)?",
            "5. Which terms should never get a page (jobs, courses, unrelated brands, navigational queries)?",
        ],
        "competitorCandidates": [
            {"name": display[k], "aiOverviewsNamingIt": n, "shareOfAIOKeywords": round(100 * n / aio_n) if aio_n else 0,
             "likelyDomain": dom_for[k].most_common(1)[0][0] if dom_for[k] else None}
            for k, n in named.most_common(25)
        ],
        "categories": [{"category": k, **v} for k, v in sorted(cats.items(), key=lambda x: -x[1]["volume"])],
        "answerTemplate": {
            "offer": "", "audience": "",
            "brandNames": [],
            "competitors": [{"name": "", "aliases": [], "domain": ""}],
            "conquest": {"include": True, "businessValue": 3},
            "businessValue": {"default": 2, "categories": {}, "keywordContains": {}},
            "skipCategories": [], "skipKeywordContains": [],
            "assumptions": [],
        },
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=1)
    print(f"Wrote {a.out}: {len(draft['competitorCandidates'])} brand candidates from {aio_n} AI Overviews, {len(cats)} categories. Ask the 5 questions, then save profile.json.")


if __name__ == "__main__":
    main()
