#!/usr/bin/env python3
"""Flag writing that reads as machine-made in the public docs.

Checks README.md, CONTRIBUTING.md, CHANGELOG.md, docs/**/*.md and skills/*/README.md for:
  - words and phrases from the banned list in skills/burn/references/style.md
  - more than one em dash in a paragraph
  - emoji in headings
  - stock openers ("In today's...", "Welcome to...")

Usage: python tests/lint_style.py [files...]
Exits 1 if anything is flagged. Code blocks and inline code are ignored.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BANNED = [
    "delve", "leverage", "leveraging", "seamless", "seamlessly", "robust", "elevate",
    "unlock", "unleash", "empower", "supercharge", "game-changer", "game changer",
    "cutting-edge", "revolutionize", "harness", "streamline", "effortless", "effortlessly",
    "embark", "tapestry", "testament", "it's worth noting", "in conclusion",
    "in today's", "fast-paced", "comprehensive guide", "look no further",
]
OPENERS = re.compile(r"^(welcome to|in this (guide|article|post)|are you tired of)", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def public_files():
    files = [ROOT / n for n in ("README.md", "CONTRIBUTING.md", "CHANGELOG.md")]
    files += sorted((ROOT / "docs").rglob("*.md"))
    files += sorted((ROOT / "skills").glob("*/README.md"))
    return [f for f in files if f.is_file()]


def strip_code(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def check(path):
    problems = []
    rel = path.relative_to(ROOT).as_posix()
    text = strip_code(path.read_text(encoding="utf-8"))
    for i, para in enumerate(re.split(r"\n\s*\n", text)):
        low = para.lower()
        for word in BANNED:
            if re.search(r"(?<![\w-])" + re.escape(word) + r"(?![\w-])", low):
                problems.append(f"{rel}: banned phrase '{word}' in: {para.strip()[:70]!r}")
        if para.count("—") > 1:
            problems.append(f"{rel}: {para.count(chr(0x2014))} em dashes in one paragraph: {para.strip()[:70]!r}")
        first = para.strip().splitlines()[0] if para.strip() else ""
        if first.startswith("#") and EMOJI.search(first):
            problems.append(f"{rel}: emoji in heading: {first!r}")
        if OPENERS.match(first):
            problems.append(f"{rel}: stock opener: {first[:70]!r}")
    return problems


def main(argv):
    files = [Path(a).resolve() for a in argv] if argv else public_files()
    problems = [p for f in files for p in check(f)]
    if problems:
        print("\n".join(problems))
        print(f"\n{len(problems)} style problem(s)")
        return 1
    print(f"ok: {len(files)} public docs checked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
