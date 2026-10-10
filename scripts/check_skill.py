#!/usr/bin/env python3
"""Regression checks for the Design Intelligence skill (docs-only repo).

Checks:
  1. Internal links resolve to existing files.
  2. Qualified section refs ("J1 §2.9", "SKILL §5") point to a real heading.
  3. The judgment-card template (J8 §5) parses as YAML.
  4. Markdown anchors (#fragment) on internal links resolve to a heading.
  5. Hard-phrase scan (禁止 / 不得 / 一律 / 多了是 …) — informational, for human review.
  6. Context budget: characters per file and for common load sets.

Exit code 1 if any link/anchor/section/template check fails. Items 5 and 6 are informational.
Usage: python3 scripts/check_skill.py
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FILES = {"SKILL": ROOT / "SKILL.md", **{p.name[:2]: p for p in sorted((ROOT / "references").glob("J*.md"))}}

HEADING = re.compile(r"^#{2,3}\s+(\d+(?:\.\d+)?)[.\s]", re.M)
QREF = re.compile(r"\b(SKILL|J[1-8])\s*§\s*(\d+(?:\.\d+)?)")
LINK = re.compile(r"\]\(([^)#\s]+)(?:#([^)\s]*))?\)")
HARD = re.compile(r"禁止|不得|一律|绝不|不允许|多了是|至多|必须")

# Load sets used for budget reporting (see SKILL §5 default combinations).
LOAD_SETS = {
    "always (SKILL+J1)": ["SKILL", "J1"],
    "deck (SKILL+J1+J2+J4+J7+J8)": ["SKILL", "J1", "J2", "J4", "J7", "J8"],
    "poster/single page (SKILL+J1+J2+J4+J8)": ["SKILL", "J1", "J2", "J4", "J8"],
}


def headings(path):
    return set(HEADING.findall(path.read_text(encoding="utf-8")))


def slugs(path):
    """GitHub-style heading slugs (lowercase, punctuation removed, spaces -> '-')."""
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if m:
            t = re.sub(r"[^\w\- ]", "", m.group(1).strip().lower())
            out.add(t.replace(" ", "-"))
    return out


def main():
    failures = []
    heads = {k: headings(v) for k, v in FILES.items()}

    # 1 + 2: links and qualified section refs
    for key, path in FILES.items():
        text = path.read_text(encoding="utf-8")
        for m in LINK.finditer(text):
            target = (path.parent / m.group(1)).resolve()
            if not target.exists():
                failures.append(f"{path.name}: broken link -> {m.group(1)}")
            elif m.group(2) and target.suffix == ".md":
                # 4: anchor must match a heading slug in the target file
                if m.group(2) not in slugs(target):
                    failures.append(f"{path.name}: broken anchor -> {m.group(1)}#{m.group(2)}")
        for m in QREF.finditer(text):
            doc, sec = m.group(1), m.group(2)
            if sec not in heads[doc]:
                failures.append(f"{path.name}: {doc} §{sec} has no matching heading")

    # 3: judgment card template (lives in J8 §5)
    j8 = FILES["J8"].read_text(encoding="utf-8")
    block = re.search(r"```yaml\n(judgment_card:.*?)```", j8, re.S)
    if not block:
        failures.append("J8: judgment_card yaml block not found")
    else:
        try:
            card = yaml.safe_load(block.group(1))["judgment_card"]
            for k in ["strategy", "medium", "spatial", "system", "per_page", "rhythm", "not_doing"]:
                if k not in card:
                    failures.append(f"J8 judgment_card missing key: {k}")
        except yaml.YAMLError as e:
            failures.append(f"J8 judgment_card YAML error: {e}")

    # 5: hard-phrase scan (informational; each hit is a candidate for a 启发式/区间 rewrite)
    print("\n== Hard-phrase scan (informational, review by hand) ==")
    for key, path in FILES.items():
        hits = [(i + 1, ln.strip()) for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines()) if HARD.search(ln)]
        if hits:
            print(f"  {path.name}: {len(hits)} line(s)")
            for n, ln in hits:
                print(f"    L{n}: {ln[:90]}")

    # 6: budget (informational)
    chars = {k: len(v.read_text(encoding="utf-8")) for k, v in FILES.items()}
    print("== Context budget (characters, informational) ==")
    for k, v in chars.items():
        print(f"  {k:6s} {v:7d}")
    print(f"  {'total':6s} {sum(chars.values()):7d}")
    for name, keys in LOAD_SETS.items():
        print(f"  load set {name}: {sum(chars[k] for k in keys)}")

    print("\n== Reference / template checks ==")
    if failures:
        for f in failures:
            print("  FAIL", f)
        print(f"{len(failures)} failure(s)")
        return 1
    print("  all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
