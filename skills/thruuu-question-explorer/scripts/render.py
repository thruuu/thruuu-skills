#!/usr/bin/env python3
"""Validate the question explorer data and splice it into the HTML template.

Usage: python3 render.py <data.json> <out.html>

Stdlib only, no network. Exit 1 with a message on invalid data.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "references", "question-explorer.template.html")
BLOCK = re.compile(r'(^<script type="application/json" id="qe-data">\n)(.*?)(\n</script>)', re.S | re.M)

STR_KEYS = ("seed", "country", "language", "device", "date")
NUM_KEYS = ("creditsUsed", "searchesRun", "questionsFound", "repeatedSkipped")


def fail(msg):
    sys.stderr.write("render.py: " + msg + "\n")
    sys.exit(1)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_meta(meta):
    if not isinstance(meta, dict):
        fail("meta must be an object")
    for k in STR_KEYS:
        if not isinstance(meta.get(k), str):
            fail("meta." + k + " must be a string")
    for k in NUM_KEYS:
        if not is_num(meta.get(k)):
            fail("meta." + k + " must be a number")
    if "view" in meta and meta["view"] not in ("questions", "brands"):
        fail("meta.view must be 'questions' or 'brands'")
    if "highlightBrand" in meta and not isinstance(meta["highlightBrand"], str):
        fail("meta.highlightBrand must be a string")


def dedupe_brands(brands, path):
    if not isinstance(brands, list) or not all(isinstance(b, str) for b in brands):
        fail(path + ".brands must be a list of strings")
    seen, out = set(), []
    for b in brands:
        b = b.strip()
        if b and b.lower() not in seen:
            seen.add(b.lower())
            out.append(b)
    return out


def walk(node, path, stats, brands_seen):
    """Validate one node, normalise it in place. Returns nothing."""
    if isinstance(node, str):
        if not node.strip():
            fail(path + " is an empty string")
        stats["nodes"] += 1
        return
    if not isinstance(node, dict):
        fail(path + " must be a string or an object")
    if not isinstance(node.get("q"), str) or not node["q"].strip():
        fail(path + ".q must be a non-empty string")
    url = node.get("thruuuUrl")
    if url is not None and (not isinstance(url, str) or not (url.startswith("https://") or url == "#")):
        fail(path + ".thruuuUrl must start with https:// (or be # for no link)")
    if "aio" in node and node["aio"] not in ("present", "absent", "degraded"):
        fail(path + ".aio must be present, absent or degraded")
    if "brands" in node:
        node["brands"] = dedupe_brands(node["brands"], path)
        for b in node["brands"]:
            brands_seen.add(b.lower())
    rs = node.get("relatedSearches")
    if "relatedSearches" in node and (not isinstance(rs, list) or not all(isinstance(r, str) and r.strip() for r in rs)):
        fail(path + ".relatedSearches must be a list of non-empty strings")
    paa = node.get("paa", [])
    if not isinstance(paa, list):
        fail(path + ".paa must be a list")
    for i, child in enumerate(paa):
        stats["nodes"] += 1
        walk_child(child, path + ".paa[" + str(i) + "]", stats, brands_seen)


def walk_child(child, path, stats, brands_seen):
    if isinstance(child, str):
        if not child.strip():
            fail(path + " is an empty string")
        return
    # object child: count was added by the caller, recurse for its own children
    walk(child, path, stats, brands_seen)


def safe_json(data):
    s = json.dumps(data, ensure_ascii=False)
    s = s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    s = s.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return s


def main():
    if len(sys.argv) != 3:
        fail("usage: render.py <data.json> <out.html>")
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        fail("cannot read data: " + str(e))
    if not isinstance(data, dict):
        fail("data must be an object with meta and tree")
    check_meta(data.get("meta"))
    tree = data.get("tree")
    if not isinstance(tree, dict) or not isinstance(tree.get("q"), str) or not tree["q"].strip():
        fail("tree.q must be a non-empty string")

    stats = {"nodes": 0}
    brands_seen = set()
    walk(tree, "tree", stats, brands_seen)

    meta = data["meta"]
    if meta["questionsFound"] != stats["nodes"]:
        sys.stderr.write("warning: meta.questionsFound is %s but the tree draws %s questions (levels 1 to 3)\n"
                         % (meta["questionsFound"], stats["nodes"]))
    hb = meta.get("highlightBrand")
    if hb and hb.strip().lower() not in brands_seen:
        sys.stderr.write("warning: highlightBrand '%s' is not in any node's brands\n" % hb)

    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    m = BLOCK.search(tpl)
    if not m:
        fail("template has no qe-data block")
    html = tpl[:m.start(2)] + safe_json(data) + tpl[m.end(2):]
    out = os.path.abspath(sys.argv[2])
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(out)


if __name__ == "__main__":
    main()
