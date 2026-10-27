#!/usr/bin/env python3
"""Build one zip per skill in dist/, with the skill folder at the zip root.

Usage: python3 scripts/build-skill-zips.py [skill-name ...]

Upload a zip under Settings > Capabilities > Skills in claude.ai or the Claude desktop app.
Stdlib only. Skips __pycache__, .pyc files and hidden files.
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
DIST = os.path.join(ROOT, "dist")
MAX_DESCRIPTION = 1024  # claude.ai rejects a longer SKILL.md description
STAMP = (2026, 1, 1, 0, 0, 0)  # fixed timestamp so the same files give the same zip


def skip(name):
    return name == "__pycache__" or name.startswith(".") or name.endswith(".pyc")


def check_description(skill, skill_md):
    with open(skill_md, encoding="utf-8") as f:
        for line in f:
            if line.startswith("description:"):
                n = len(line[len("description:"):].strip())
                if n > MAX_DESCRIPTION:
                    sys.exit("build-skill-zips: skills/%s description is %d characters, claude.ai allows %d" % (skill, n, MAX_DESCRIPTION))
                return
    sys.exit("build-skill-zips: skills/%s has no description in SKILL.md" % skill)


def build(skill):
    src = os.path.join(SKILLS, skill)
    if not os.path.isfile(os.path.join(src, "SKILL.md")):
        sys.exit("build-skill-zips: skills/%s has no SKILL.md" % skill)
    check_description(skill, os.path.join(src, "SKILL.md"))
    out = os.path.join(DIST, skill + ".zip")
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if not skip(d))
            for f in sorted(files):
                if skip(f):
                    continue
                path = os.path.join(base, f)
                info = zipfile.ZipInfo(os.path.join(skill, os.path.relpath(path, src)).replace(os.sep, "/"), STAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o755 if os.access(path, os.X_OK) else 0o644) << 16
                with open(path, "rb") as fh:
                    z.writestr(info, fh.read())
                count += 1
    print("%s (%d files)" % (out, count))


def main():
    names = sys.argv[1:] or sorted(d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d)) and not skip(d))
    os.makedirs(DIST, exist_ok=True)
    for n in names:
        build(n)


if __name__ == "__main__":
    main()
