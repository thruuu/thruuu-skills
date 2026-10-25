#!/usr/bin/env python3
"""Validate the question explorer data and splice it into the HTML template.

Usage: python3 render.py <data.json> <out.html>   build the page
       python3 render.py <data.json> --text       print the lists for chat (no page)

Also derives the article groups, the all-questions list, related-search modifiers and the
plan flags. Stdlib only, no network. Exit 1 with a message on invalid data.
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

SHARE = 4          # shared top-10 URLs that put a question in a group
SIMILAR = 0.6      # word overlap that places two questions next to each other
STOP = set("a an the is are was were be do does did can could should would will of for to in on at by with and or than vs versus i you we my your me it its this that what which who how why when where about as from into".split())
# capabilities by plan name (first word, lower case)
PLAN_RULES = {
    "free": dict(aio=False, brands=False, cluster=False, report=False, cap=0),
    "trial": dict(aio=True, brands=True, cluster=True, report=True, cap=500),
    "payg": dict(aio=False, brands=False, cluster=True, report=False, cap=2000),
    "starter": dict(aio=False, brands=False, cluster=True, report=False, cap=2000),
    "professional": dict(aio=True, brands=False, cluster=True, report=True, cap=2000),
    "agency": dict(aio=True, brands=True, cluster=True, report=True, cap=2000),
}
SRC_ORDER = ("paa", "page", "aio")
SRC_LABEL = {"paa": "People Also Asked", "page": "Page headings", "aio": "AI Overview sources"}
LOGID = re.compile(r"[0-9a-f]{24}$")

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
    if "view" in meta and meta["view"] not in ("tree", "all", "groups", "brands", "questions"):
        fail("meta.view must be tree, all, groups or brands")
    if "highlightBrand" in meta and not isinstance(meta["highlightBrand"], str):
        fail("meta.highlightBrand must be a string")
    for k in ("aioIncluded", "brandsIncluded"):
        if k in meta and not isinstance(meta[k], bool):
            fail("meta." + k + " must be true or false")
    if "plan" in meta and not isinstance(meta["plan"], str):
        fail("meta.plan must be a string")
    if (meta.get("aioIncluded") is False or meta.get("brandsIncluded") is False) and not (meta.get("plan") or "").strip():
        fail("meta.plan must be a plan name when meta.aioIncluded or meta.brandsIncluded is false")


def plan_flags(meta):
    """Resolve what the plan includes and write the flags back into meta."""
    name = (meta.get("plan") or "").strip().lower().split(" ")[0]
    r = PLAN_RULES.get(name, dict(aio=True, brands=True, cluster=True, report=True, cap=2000))
    aio = meta["aioIncluded"] if "aioIncluded" in meta else r["aio"]
    brands = meta["brandsIncluded"] if "brandsIncluded" in meta else r["brands"]
    meta["aioIncluded"] = aio
    meta["brandsIncluded"] = aio and brands
    meta["clusterIncluded"] = r["cluster"]
    meta["reportIncluded"] = r["report"]
    meta["clusterCap"] = r["cap"]
    if "plan" not in meta or not meta["plan"].strip():
        meta["plan"] = ""


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
    for k in keep:
        if parent[k] == k and " " not in k and "." not in k:
            hit = [q for q in keep if parent[q] != q and k in q.split()]
            if hit:
                parent[k] = parent[hit[0]]
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
    for key in ("urls", "paaAll"):
        v = node.get(key)
        if key in node and (not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v)):
            fail(path + "." + key + " must be a list of non-empty strings")
    if "urls" in node:
        node["urls"] = [u.strip() for u in node["urls"] if u.strip().startswith("https://") or u.strip().startswith("http://")]
    rows = node.get("topicRows")
    if "topicRows" in node and (not isinstance(rows, list) or not all(isinstance(r, dict) and isinstance(r.get("term"), str) for r in rows)):
        fail(path + ".topicRows must be a list of objects with a term")
    sid = node.get("scrapeLogId")
    if sid is not None and not (isinstance(sid, str) and LOGID.match(sid)):
        fail(path + ".scrapeLogId must be the 24 character Scrape Log ID")
    if sid is None and isinstance(url, str) and LOGID.match(url.rstrip("/").split("/")[-1]):
        node["scrapeLogId"] = url.rstrip("/").split("/")[-1]
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



def tokens(s):
    out = set()
    for w in re.findall(r"\w+", s.lower()):
        if w in STOP:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


def similar(a, b):
    if not a or not b:
        return False
    if a == b:
        return True
    if min(len(a), len(b)) < 3:
        return False
    return len(a & b) / float(len(a | b)) >= SIMILAR


def url_key(u):
    u = re.sub(r"^https?://(www\.)?", "", u.strip().lower())
    return re.split(r"[?#]", u)[0].rstrip("/")


def top10(node):
    seen, out = set(), []
    for u in node.get("urls", []):
        k = url_key(u)
        if k and k not in seen:
            seen.add(k)
            out.append(k)
        if len(out) == 10:
            break
    return out


def intent(q):
    s = norm_q(q)
    if re.match(r"^(how (much|many|long|often)|what is the (difference|cost|price))", s):
        return "Explainer"
    if re.match(r"^what is the best (?!way)", s):
        return "Comparison"
    if re.match(r"^(how|what is the best way)", s):
        return "How-to"
    if re.match(r"^what are (the best|some)", s):
        return "Listicle"
    if re.match(r"^(which|who)", s):
        return "Comparison"
    if re.match(r"^(is|are|can|does|do|should|will)\b", s):
        return "Evaluative"
    return "Explainer"


def topic_ok(term, seed_tokens):
    t = norm_q(term)
    return bool(t) and not (" " not in t and t in seed_tokens)


def prep_nodes(tree, meta):
    """Per node: related-search modifiers, topics without seed-only words, tree order list."""
    seed_tokens = set(re.findall(r"\w+", meta["seed"].lower()))
    for n in each_node(tree):
        base = norm_q(n["q"])
        mods, rest = [], []
        for r in n.get("relatedSearches", []):
            k = norm_q(r)
            if k.startswith(base + " "):
                mods.append(k[len(base) + 1:])
            else:
                rest.append(r)
        n["relatedModifiers"] = mods
        if "relatedSearches" in n:
            n["relatedSearches"] = rest
        if "topics" in n:
            n["topics"] = [t for t in n["topics"] if topic_ok(t, seed_tokens)]
        if "topicRows" in n:
            n["topicRows"] = [r for r in n["topicRows"] if topic_ok(r["term"], seed_tokens)]
    return seed_tokens


def order_items(node, parent=None):
    """Depth first, seed first. Yields (item, parent) for dict and string nodes."""
    yield node, parent
    if isinstance(node, dict):
        for c in node.get("paa", []):
            for x in order_items(c, node):
                yield x


def brief_prompt(q, sid):
    return 'Create a brief from the SERP analysis %s for "%s".' % (sid, q)


def build_groups(tree, meta):
    groups, of_node = [], {}
    for item, parent in order_items(tree):
        if isinstance(item, dict) and item.get("analysed", True) is not False:
            urls = top10(item)
            home = None
            if urls:
                for g in groups:
                    shared = len(set(urls) & set(g["urls"]))
                    if g["urls"] and shared >= SHARE:
                        home = (g, shared)
                        break
            if home:
                g, shared = home
            else:
                g, shared = {"lead": item, "urls": urls, "members": [], "leaves": []}, None
                groups.append(g)
            g["members"].append((item, shared))
            of_node[id(item)] = g
        else:
            q = item if isinstance(item, str) else item["q"]
            g = of_node.get(id(parent)) if parent is not None else None
            if g is not None:
                g["leaves"].append(q)
    out = []
    for i, g in enumerate(groups):
        num = i + 1
        lead = g["lead"]
        have = {norm_q(n["q"]) for n, _ in g["members"]}
        leaves = []
        for q in g["leaves"]:
            if norm_q(q) not in have:
                have.add(norm_q(q))
                leaves.append(q)
        h2, seen = [], set(norm_q(n["q"]) for n, _ in g["members"])
        for src_key, label in (("headingQuestions", "page"), ("citedQuestions", "aio")):
            for n, _ in g["members"]:
                for it in n.get(src_key, []):
                    k = norm_q(it["q"])
                    if k in seen and label == "aio":
                        continue
                    hit = next((x for x in h2 if norm_q(x["q"]) == k), None)
                    if hit:
                        if label == "page":
                            hit["count"] = max(hit["count"], it["count"])
                    elif k not in seen:
                        h2.append({"q": it["q"], "count": it["count"], "src": label})
        h2.sort(key=lambda x: (x["src"] != "page", -x["count"]))
        m = len(g["members"])
        tmap, order = {}, []
        for n, _ in g["members"]:
            rows = n.get("topicRows") or [{"term": t} for t in n.get("topics", [])]
            for r in rows:
                k = norm_q(r["term"])
                if k not in tmap:
                    tmap[k] = {"term": r["term"], "n": 0, "foundOn": r.get("foundOn")}
                    order.append(k)
                tmap[k]["n"] += 1
        topics = []
        for k in sorted(order, key=lambda k: -tmap[k]["n"])[:8]:
            t = tmap[k]
            if m > 1:
                label = "%d of %d searches" % (t["n"], m)
            else:
                label = t["foundOn"] if isinstance(t["foundOn"], str) else ""
            topics.append({"term": t["term"], "label": label})
        shares = [s for _, s in g["members"] if s is not None]
        if shares:
            lo, hi = min(shares), max(shares)
            rng = str(lo) if lo == hi else "%d to %d" % (lo, hi)
            why = "%d more search%s %s %s of the lead's top 10 results." % (m - 1, "" if m == 2 else "es", "shares" if m == 2 else "share", rng)
        elif g["urls"]:
            why = "No other search shares %d or more of its top 10 results." % SHARE
        else:
            why = "Result URLs were not captured for this search, so it stands alone."
        members = []
        for n, s in g["members"]:
            sid = n.get("scrapeLogId")
            members.append({"q": n["q"], "scrapeLogId": sid, "thruuuUrl": n.get("thruuuUrl"), "aio": n.get("aio"),
                            "shared": s, "prompt": brief_prompt(n["q"], sid) if sid else None})
            n["group"] = num
        out.append({"num": num, "lead": lead["q"], "intent": intent(lead["q"]), "members": members, "leaves": leaves,
                    "aioCount": sum(1 for n, _ in g["members"] if n.get("aio") in ("present", "degraded")),
                    "h2": h2, "topics": topics, "why": why})
    return out


def build_all_questions(tree, meta):
    """Every question found, merged by wording, similar ones side by side, sorted by count."""
    seed_key = norm_q(meta["seed"])
    rows, order = {}, []

    def add(q, src):
        k = norm_q(q)
        if not k or k == seed_key:
            return
        if k not in rows:
            rows[k] = {"q": q, "n": 0, "src": set(), "idx": len(order)}
            order.append(k)
        rows[k]["n"] += 1
        rows[k]["src"].add(src)

    for n in each_node(tree):
        if n.get("analysed", True) is False:
            continue
        for q in n.get("paaAll") or [c if isinstance(c, str) else c["q"] for c in n.get("paa", [])]:
            add(q, "paa")
        for it in n.get("headingQuestions", []):
            add(it["q"], "page")
        for it in n.get("citedQuestions", []):
            add(it["q"], "aio")
    ranked = sorted(order, key=lambda k: (-rows[k]["n"], rows[k]["idx"]))
    clusters = []
    for k in ranked:
        t = tokens(rows[k]["q"])
        for c in clusters:
            if similar(t, c["tok"]):
                c["keys"].append(k)
                break
        else:
            clusters.append({"tok": t, "keys": [k]})
    out = []
    for ci, c in enumerate(clusters):
        for k in c["keys"]:
            r = rows[k]
            out.append({"q": r["q"], "n": r["n"], "sources": [SRC_LABEL[s] for s in SRC_ORDER if s in r["src"]], "cluster": ci})
    return out


def cluster_prompt(meta, rows):
    cap = meta["clusterCap"]
    qs = [meta["seed"]] + [r["q"] for r in rows]
    cut = qs[:cap] if cap else qs
    return len(qs), len(cut), 'Create a topic cluster from these %d questions about "%s":\n' % (len(cut), meta["seed"]) + "\n".join("- " + q for q in cut)


def text_report(data):
    meta, tree = data["meta"], data["tree"]
    L = ["# Article groups (%d)" % len(data["groups"]), ""]
    for g in data["groups"]:
        bits = [g["intent"]]
        if meta["aioIncluded"]:
            bits.append("AI Overview on %d of %d" % (g["aioCount"], len(g["members"])))
        L.append("%d. %s (%s)" % (g["num"], g["lead"], ", ".join(bits)))
        L.append("   Searched: " + "; ".join(m["q"] for m in g["members"]))
        if g["leaves"]:
            L.append("   Also asked: " + "; ".join(g["leaves"]))
        if g["h2"]:
            L.append("   H2 candidates: " + "; ".join(x["q"] for x in g["h2"][:6]))
        L.append("   " + g["why"])
        if g["members"][0]["prompt"]:
            L.append("   Brief: " + g["members"][0]["prompt"])
    L += ["", "# All questions (%d, similar ones together, by count)" % len(data["allQuestions"]), ""]
    for r in data["allQuestions"]:
        L.append("- %s%s [%s]" % (r["q"], " x%d" % r["n"] if r["n"] > 1 else "", ", ".join(r["sources"])))
    if meta["aioIncluded"] and meta["brandsIncluded"]:
        bm = {}
        for n in each_node(tree):
            for b in n.get("brands", []):
                bm.setdefault(b, []).append(n["q"])
        own = {b.lower() for b in meta.get("topicBrands", [])}
        ranked = sorted(bm, key=lambda b: (b.lower() in own, -len(bm[b]), b))
        L += ["", "# Brands named in AI Overviews", ""]
        for b in ranked:
            L.append("- %s: %d question%s%s" % (b, len(bm[b]), "" if len(bm[b]) == 1 else "s", " (your topic)" if b.lower() in own else ""))
    return "\n".join(L)


def apply_brands(tree, meta):
    if not meta["aioIncluded"]:
        for n in each_node(tree):
            for k in ("brands", "aio", "citedQuestions"):
                n.pop(k, None)
        meta["brandVariants"], meta["topicBrands"] = {}, []
        return
    if not meta["brandsIncluded"]:
        for n in each_node(tree):
            n.pop("brands", None)
        meta["brandVariants"], meta["topicBrands"] = {}, []
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
    text = len(sys.argv) == 3 and sys.argv[2] == "--text"
    if len(sys.argv) != 3:
        fail("usage: render.py <data.json> <out.html | --text>")
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
    plan_flags(meta)
    apply_brands(tree, meta)
    prep_nodes(tree, meta)
    meta["headingsDropped"] = stats["dropped"]
    meta.setdefault("view", "tree")
    if meta["view"] == "questions":
        meta["view"] = "tree"
    data["groups"] = build_groups(tree, meta)
    data["allQuestions"] = build_all_questions(tree, meta)
    total, shown, prompt = cluster_prompt(meta, data["allQuestions"])
    data["cluster"] = {"total": total, "shown": shown, "prompt": prompt}
    data["urlsMissing"] = not any(n.get("urls") for n in each_node(tree))
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
    if data["urlsMissing"]:
        sys.stderr.write("warning: no node carries result URLs, so every searched question is its own article group\n")

    if text:
        base = os.path.splitext(os.path.abspath(sys.argv[1]))[0]
        with open(base + ".cleaned.json", "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=1)
        print(text_report(data))
        return
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
