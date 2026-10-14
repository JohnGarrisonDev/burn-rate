#!/usr/bin/env python3
"""Lint the skills in this repo.

Checks, for every folder under skills/:
  - SKILL.md exists and starts with YAML frontmatter
  - frontmatter has `name` and `description`
  - `name` matches the folder name and is lowercase-kebab
  - `description` is non-empty and under 1024 characters
  - every relative Markdown link in every .md file under skills/ resolves

Usage: python tests/lint_skills.py
Exits 1 if anything fails. Stdlib only.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def check_skill(folder):
    errors = []
    skill_md = folder / "SKILL.md"
    if not skill_md.is_file():
        return [f"{folder.name}: missing SKILL.md"]
    fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    if fm is None:
        return [f"{folder.name}: SKILL.md has no frontmatter block"]
    name = fm.get("name", "")
    desc = fm.get("description", "")
    if not name:
        errors.append(f"{folder.name}: frontmatter missing `name`")
    elif name != folder.name:
        errors.append(f"{folder.name}: name `{name}` does not match folder")
    elif not NAME_RE.match(name):
        errors.append(f"{folder.name}: name must be lowercase-kebab")
    if not desc:
        errors.append(f"{folder.name}: frontmatter missing `description`")
    elif len(desc) > 1024:
        errors.append(f"{folder.name}: description is {len(desc)} chars (max 1024)")
    return errors


def check_links(md_file):
    errors = []
    text = md_file.read_text(encoding="utf-8")
    # Ignore links inside fenced code blocks.
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    for target in LINK_RE.findall(text):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            continue
        path = target.split("#", 1)[0]
        if not path:
            continue
        if not (md_file.parent / path).exists():
            rel = md_file.relative_to(ROOT).as_posix()
            errors.append(f"{rel}: broken link -> {target}")
    return errors


def main():
    if not SKILLS.is_dir():
        print("no skills/ folder found")
        return 1
    errors = []
    folders = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    for folder in folders:
        errors += check_skill(folder)
    for md in sorted(SKILLS.rglob("*.md")):
        errors += check_links(md)
    for md in sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").rglob("*.md")):
        errors += check_links(md)
    if errors:
        print("\n".join(errors))
        print(f"\n{len(errors)} problem(s) in {len(folders)} skills")
        return 1
    print(f"ok: {len(folders)} skills checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
