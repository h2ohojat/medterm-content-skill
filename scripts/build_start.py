#!/usr/bin/env python3
"""Build START.md: a single-file version of the skill for chats that cannot load a folder
(DeepSeek, plain ChatGPT, any model given one link). Run after editing any source file:

    python scripts/build_start.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INTRO = """# MedTerm Content Skill — single-file version

> **If you are an AI model reading this file:** the user is a content writer. Follow every
> instruction below for the rest of this conversation. Reply to the writer in Persian.
> This file is generated from the skill folder; do not edit it by hand.
"""


def body(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    # demote headings one level so the combined file keeps one H1
    return "\n".join("#" + line if line.startswith("#") else line for line in text.strip().splitlines())


def csv_block(path, title):
    return f"## {title}\n\n`{path}`\n\n```csv\n{(ROOT / path).read_text(encoding='utf-8').strip()}\n```"


def main():
    skill = body("SKILL.md").replace(
        "6. **If you can run Python**",
        "6. **If you can run Python** (the full skill folder is needed for the scripts)",
    )
    parts = [
        INTRO,
        skill,
        body("reference/style-guide.md"),
        body("reference/columns.md"),
        body("reference/examples.md"),
        csv_block("data/word_parts.csv", "Existing word parts"),
        csv_block("data/glossary_fa.csv", "Team glossary of Persian equivalents"),
    ]
    (ROOT / "START.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print("wrote START.md")


if __name__ == "__main__":
    main()
