#!/usr/bin/env python3
"""Validate the question explorer data and splice it into the HTML template.

Usage: python3 render.py <data.json> <out.html>

Stdlib only, no network. Exit 1 with a message on invalid data.
"""
import copy
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "references", "question-explorer.template.html")
BLOCK = re.compile(r'(^<script type="application/json" id="qe-data">\n)(.*?)(\n</script>)', re.S | re.M)

FAQ_MARK = re.compile(r"^\s*(?:[Qq]\d*[.:]|\d+[.)])\s+")
FIRST_PERSON = re.compile(r"^(how|what|why)\s+(i|we)\b", re.I)
FURNITURE = re.compile(r"^(ready for more|who this (course|guide) is for|what you should have now|how this helps|table of contents)$")
TAIL = re.compile(r"[\s?!.,;:]+$")

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
    if "aioIncluded" in meta and not isinstance(meta["aioIncluded"], bool):
        fail("meta.aioIncluded must be true or false")
    if meta.get("aioIncluded") is False and (not isinstance(meta.get("plan"), str) or not meta["plan"].strip()):
        fail("meta.plan must be a plan name when meta.aioIncluded is false")


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


def norm_q(s):
    return TAIL.sub("", " ".join(s.lower().split()))


def clean_counted(rows, path, stats):
    """Strip FAQ markers, merge repeats (sum counts), drop first-person and page furniture. Keeps count order."""
    if not isinstance(rows, list):
        fail(path + " must be a list")
    merged, order = {}, []
    for i, r in enumerate(rows):
        if not isinstance(r, dict) or not isinstance(r.get("q"), str) or not is_num(r.get("count")):
            fail(path + "[" + str(i) + "] must be an object with q (string) and count (number)")
        q = FAQ_MARK.sub("", r["q"]).strip()
        k = norm_q(q)
        if not k:
            stats["dropped"] += 1
        elif FIRST_PERSON.match(k) or FURNITURE.match(k):
            stats["dropped"] += 1
        elif k in merged:
            merged[k]["count"] += r["count"]
        else:
            merged[k] = {"q": q, "count": r["count"]}
            order.append(k)
    out = [merged[k] for k in order]
    out.sort(key=lambda r: -r["count"])
    return out


def fold_brands(all_brands, seed):
    """Returns (map lower name -> parent display name or None if dropped, variants by parent key, topic keys)."""
    names = {}
    for b in all_brands:
        names.setdefault(b.lower(), b)
    keep = {k: v for k, v in names.items() if not k.endswith(".md") and "group" not in k}
    parent = {}
    for k in keep:
        cands = [p for p in keep if p != k and (k.startswith(p + " ") or k.startswith(p + "."))]
        # the shortest listed brand is the root; chains such as "a b c" fold to "a"
        parent[k] = min(cands, key=len) if cands else k
    variants = {}
    for k, p in parent.items():
        if k != p:
            variants.setdefault(p, []).append(keep[k])
    mapping = {k: (keep[parent[k]] if k in keep else None) for k in names}
    tokens = set(re.findall(r"\w+", seed.lower()))
    topic = sorted(p for p in set(parent.values()) if p in tokens)
    return mapping, variants, topic


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
    if "topics" in node and (not isinstance(node["topics"], list) or not all(isinstance(t, str) for t in node["topics"])):
        fail(path + ".topics must be a list of strings")
    for key in ("headingQuestions", "citedQuestions"):
        if key in node:
            node[key] = clean_counted(node[key], path + "." + key, stats)
    node.pop("aioQuestions", None)
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


def each_node(node):
    if isinstance(node, dict):
        yield node
        for c in node.get("paa", []):
            for x in each_node(c):
                yield x


def apply_brands(tree, meta):
    if meta.get("aioIncluded") is False:
        for n in each_node(tree):
            for k in ("brands", "aio", "citedQuestions"):
                n.pop(k, None)
        return
    allb = [b for n in each_node(tree) for b in n.get("brands", [])]
    mapping, variants, topic = fold_brands(allb, meta["seed"])
    for n in each_node(tree):
        if "brands" in n:
            seen, out = set(), []
            for b in n["brands"]:
                p = mapping.get(b.lower())
                if p and p.lower() not in seen:
                    seen.add(p.lower())
                    out.append(p)
            n["brands"] = out
    meta["brandVariants"] = {k: v for k, v in variants.items()}
    meta["topicBrands"] = topic


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

    stats = {"nodes": 0, "dropped": 0}
    brands_seen = set()
    walk(tree, "tree", stats, brands_seen)

    meta = data["meta"]
    apply_brands(tree, meta)
    meta["headingsDropped"] = stats["dropped"]
    cleaned = copy.deepcopy(data)
    for n in each_node(tree):
        for k in ("headingQuestions", "citedQuestions"):
            if k in n:
                n[k] = n[k][:10]
    brands_seen = {b.lower() for n in each_node(tree) for b in n.get("brands", [])}
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
    with open(os.path.splitext(out)[0] + ".cleaned.json", "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=1)
    print(out)


if __name__ == "__main__":
    main()
