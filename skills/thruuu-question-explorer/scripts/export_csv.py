#!/usr/bin/env python3
"""Write the question explorer rows to a CSV file.

Usage: python3 export_csv.py <rows.json> <out.csv>

Stdlib only, no network. Exit 1 with a message on invalid input.
"""
import csv
import json
import os
import re
import sys

HEADER = ["type", "text", "paa_level", "serp_query", "page_count",
          "topic_found_on", "topic_avg_uses", "repeat_in_tree", "thruuu_url"]
INPUT_KEYS = set(HEADER) - {"repeat_in_tree"}
TYPES = ("paa", "heading_question", "topic", "related_search")
TAIL = re.compile(r"[\s?!.,;:]+$")


def fail(msg):
    sys.stderr.write("export_csv.py: " + msg + "\n")
    sys.exit(1)


def norm(s):
    return TAIL.sub("", " ".join(s.lower().split()))


def guard(v):
    if isinstance(v, str) and v and v[0] in "=+-@\t\r":
        return "'" + v
    return v


def check_row(r, i):
    p = "row " + str(i) + ": "
    if not isinstance(r, dict):
        fail(p + "must be an object")
    extra = set(r) - INPUT_KEYS
    if extra:
        fail(p + "unknown keys " + ", ".join(sorted(extra)))
    if r.get("type") not in TYPES:
        fail(p + "type must be one of " + ", ".join(TYPES))
    for k in ("text", "serp_query"):
        if not isinstance(r.get(k), str) or not r[k].strip():
            fail(p + k + " must be a non-empty string")
    if "paa_level" in r:
        v = r["paa_level"]
        if r["type"] != "paa" or isinstance(v, bool) or v not in (1, 2, 3):
            fail(p + "paa_level must be 1 to 3 and only on paa rows")
    if "page_count" in r:
        v = r["page_count"]
        if r["type"] != "heading_question" or isinstance(v, bool) or not isinstance(v, int) or v < 1:
            fail(p + "page_count must be a positive integer and only on heading_question rows")
    for k in ("topic_found_on", "topic_avg_uses"):
        if k in r and not isinstance(r[k], str):
            fail(p + k + " must be a string")
    u = r.get("thruuu_url", "")
    if not isinstance(u, str) or (u and not u.startswith("https://")):
        fail(p + "thruuu_url must be empty or start with https://")


def main():
    if len(sys.argv) != 3:
        fail("usage: export_csv.py <rows.json> <out.csv>")
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            rows = json.load(f)
    except (OSError, ValueError) as e:
        fail("cannot read rows: " + str(e))
    if not isinstance(rows, list):
        fail("input must be a list of objects")
    for i, r in enumerate(rows):
        check_row(r, i)

    counts = {}
    for r in rows:
        k = (r["type"], norm(r["text"]))
        counts[k] = counts.get(k, 0) + 1

    out = os.path.abspath(sys.argv[2])
    per_type = {t: 0 for t in TYPES}
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        w.writerow(HEADER)
        for r in rows:
            per_type[r["type"]] += 1
            r = dict(r)
            if counts[(r["type"], norm(r["text"]))] > 1:
                r["repeat_in_tree"] = "yes"
            w.writerow([guard(r.get(h, "")) for h in HEADER])
    print(out)
    print(", ".join("%s: %d" % (t, per_type[t]) for t in TYPES) + ", total: %d" % len(rows))


if __name__ == "__main__":
    main()
