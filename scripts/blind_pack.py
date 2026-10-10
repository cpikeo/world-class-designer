#!/usr/bin/env python3
"""Blind-pack paired outputs for review.

For each task, takes the output of version A and version B, assigns them to
X / Y at random, and writes:
  <out>/review/<task>/X/...   copies of A or B's files (names neutralised)
  <out>/review/<task>/Y/...
  <out>/key/<task>.json       mapping (keep away from reviewers)

The review tree contains no version labels, file names from the originals,
or paths that reveal the version.

Usage:
  python3 scripts/blind_pack.py --a DIR_A --b DIR_B --out DIR_OUT --seed 2026 \
      [--tasks T1 T2 ...]

DIR_A / DIR_B must contain one sub-directory per task id (e.g. T1/, T2/ ...).
"""
import argparse
import json
import random
import shutil
import sys
from pathlib import Path


import re

# Strings that would reveal the version or the skill to a reviewer.
LEAK = re.compile(
    r"world-class|Design Intelligence|SKILL\.md|judgment_card|判断卡|"
    r"\b7\.[0-9]+\.[0-9]+\b|\bJ[1-8]\b|\bv7\b|git\s?log|CHANGELOG",
    re.I,
)
TEXT_EXT = {".html", ".htm", ".md", ".txt", ".svg", ".json", ".yaml", ".yml", ".css", ".js"}


def leak_scan(review_dir: Path):
    """Report (not modify) text files whose content may reveal the version."""
    hits = []
    for f in review_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() in TEXT_EXT:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for m in LEAK.finditer(text):
                hits.append((str(f.relative_to(review_dir)), m.group(0)))
    return hits


def pack(a_root: Path, b_root: Path, out: Path, seed: int, tasks):
    rng = random.Random(seed)
    key_dir = out / "key"
    review_dir = out / "review"
    key_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for task in tasks:
        a_dir, b_dir = a_root / task, b_root / task
        if not a_dir.is_dir() or not b_dir.is_dir():
            print(f"skip {task}: missing output for A or B", file=sys.stderr)
            continue
        assignment = {"X": "A", "Y": "B"}
        if rng.random() < 0.5:
            assignment = {"X": "B", "Y": "A"}
        for slot, version in assignment.items():
            src = a_dir if version == "A" else b_dir
            dst = review_dir / task / slot
            dst.mkdir(parents=True, exist_ok=True)
            for f in sorted(p for p in src.rglob("*") if p.is_file()):
                # Neutral name: keep only the extension and a running index.
                idx = sum(1 for _ in dst.iterdir()) + 1
                shutil.copy2(f, dst / f"{idx:02d}{f.suffix.lower()}")
        (key_dir / f"{task}.json").write_text(
            json.dumps({"task": task, "assignment": assignment, "seed": seed},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary.append(task)
    print(f"packed {len(summary)} task(s): {', '.join(summary)}")
    hits = leak_scan(review_dir) if review_dir.exists() else []
    if hits:
        print(f"WARNING: {len(hits)} possible leak(s) in review tree — fix the content or drop the item:")
        for path, token in hits:
            print(f"  {path}: '{token}'")
    else:
        print("leak scan: no version/skill strings found in text files")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, type=Path)
    ap.add_argument("--b", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--tasks", nargs="*", default=["T1", "T2", "T3", "T4", "T5", "T6"])
    args = ap.parse_args()
    pack(args.a, args.b, args.out, args.seed, args.tasks)


if __name__ == "__main__":
    main()
