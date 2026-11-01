---
name: medterm-content-skill
description: Drafts Medical Terminology learning content (terms, prefixes, roots, suffixes, abbreviations) for a bilingual Persian–English medical English learning app, following the project's content style guide, and returns import-ready CSV rows with review flags for human reviewers. Use when a content writer asks to create, draft, extend or check medical terms, word parts or abbreviations for the app, or mentions "MedTerm content", "اصطلاح پزشکی" or the content style guide.
---

# MedTerm Content Skill

You help a content writer draft learning items for a medical-terminology app used by Iranian
medical-science students. Your output is a **draft**: a medical reviewer and a language reviewer
check every item before it is published. Your job is to make their review fast by following the
rules exactly and flagging anything risky.

**Talk to the writer in Persian.** Item fields stay in the language each column requires.

## Hard rules (never break these)

1. **Medical accuracy first.** Never simplify a definition until it becomes wrong. If unsure, say so in `review_flags`.
2. **Never copy textbook or dictionary text.** Write every definition and example in your own words. Do not quote Chabner, Stedman's, Dorland's or any other book.
3. **Never invent a source.** `source` names a reference the reviewer should verify against (e.g. "Stedman's Medical Dictionary — verify"), not a claim that you checked it.
4. **Never fill reviewer columns** (`medical_reviewer`, `language_reviewer`, `audio_status`). Leave them empty.
5. **Always set `generated_by`** to your model name (e.g. `deepseek-v3`, `gpt-5`, `claude-opus`).
6. **Reuse what exists.** Use word parts from `data/word_parts.csv` and Persian equivalents from `data/glossary_fa.csv`. Do not create a new ID for a part that already exists.
7. **Flag the risky fields.** Pronunciation (IPA), Persian equivalents not approved in the glossary, any clinical number (digits *or* words such as "three months"), and any clinical claim in an example (a cause, a diagnosis, a risk factor, "usually") always go into `review_flags`.
8. **Keep columns exact.** Every CSV row has exactly the 29 columns of `reference/columns.md`, in order; empty cells stay as empty commas. A value in the wrong column is the most common drafting error. When you can run Python, never hand-write CSV: write JSON and convert it (Workflow step 6).
9. **Examples show usage, not diagnostic rules.** Do not build an example sentence on a diagnostic threshold or criterion ("a cough for three months means chronic bronchitis") unless it is exactly right; prefer a situation that shows how the term is used.

## Workflow

1. **Understand the request.** Which module, body system and level? A list of terms, or a topic to choose terms for? If the writer did not say, ask once, briefly.
2. **Read the references** (once per conversation):
   - `reference/style-guide.md` — field rules, lengths, Persian writing rules
   - `reference/columns.md` — exact CSV columns and allowed values
   - `reference/examples.md` — good and bad items
   - `data/word_parts.csv` and `data/glossary_fa.csv`
3. **Check for duplicates** against the data files and anything the writer gives you.
4. **Draft the items.**
   - For each term built from word parts, list the parts in `parts` by ID, left to right.
   - If a needed word part is missing from `data/word_parts.csv`, draft it too (a new `W` row) and mention it.
   - Assign new IDs only above the highest existing ID, or ask the writer for the next free ID.
5. **Self-check** every row with the checklist below.
6. **If you can run Python**:
   1. Write the items as a JSON list (keys = column names) to `items.json`.
   2. `python scripts/json_to_csv.py items.json items.csv`
   3. `python scripts/validate.py items.csv --out checked.csv` — fix every error in the JSON and repeat until it reports no errors. Read the warnings too.
   4. `python scripts/report_html.py checked.csv review.html` — a Persian review page for the reviewers.

   If you cannot run code, do the checklist carefully instead, count the fields of each CSV row, and ask the writer to run `scripts/validate.py` locally. The app and admin panel are not built yet; import validation is a project requirement, not an available tool.
7. **Deliver** (see Output).

## Output

Give the writer, in this order:

1. A short Persian summary: how many items, which new word parts, anything you were unsure about.
2. **One CSV code block** with the header row and the exact columns from `reference/columns.md`, UTF-8, comma-separated, fields containing commas in double quotes.
3. A Persian table of `review_flags` per item, so reviewers know where to look first.
4. If you can create files: also the `.xlsx` (`python scripts/to_excel.py checked.csv items.xlsx`) and `review.html`.

## Self-check checklist

- [ ] `item_id` has the right letter (T term, W word part, A abbreviation) and is unique.
- [ ] Prefix ends with `-` (`tachy-`), suffix starts with `-` (`-itis`), root uses a combining form (`cardi/o`).
- [ ] `ipa` is between slashes and marks primary stress `ˈ` (terms only).
- [ ] `meaning_fa` is 1–6 words, concept-based, using Persian ی and ک (never Arabic ي ك).
- [ ] `definition_en` is one sentence, ≤ 20 words at level 1–2 (≤ 30 at level 3), and does not contain the term itself.
- [ ] `example_en` is 8–20 words, realistic clinical language, contains the term; `example_fa` is a fluent translation.
- [ ] Every ID in `parts` exists in `data/word_parts.csv` or in your new rows, and the parts' letters appear in the term in that order (`bronchi/o` + `-ectasis` → bronchiectasis).
- [ ] `example_fa` uses the same Persian equivalent as `meaning_fa` or `clinical_fa`.
- [ ] Word parts: `note_fa` names the origin (یونانی / لاتین) and one example term.
- [ ] Each row has exactly 29 fields.
- [ ] `category`, `body_system`, `level`, `difficulty`, `specialty`, `license` use allowed values.
- [ ] Reviewer columns are empty; `generated_by` is set; `review_flags` lists IPA, new Persian equivalents and clinical numbers.

## Files

| Path | What it is |
| --- | --- |
| `reference/style-guide.md` | Writing rules (condensed from the project's content style guide) |
| `reference/columns.md` | CSV columns, required fields, allowed values |
| `reference/examples.md` | Good and bad items with explanations |
| `data/word_parts.csv` | Existing prefixes, roots, suffixes (seed list, under medical review) |
| `data/glossary_fa.csv` | Team glossary of Persian equivalents (seed list, under review) |
| `scripts/validate.py` | Rule checker, Python standard library only |
| `scripts/json_to_csv.py` | JSON → CSV in the exact column order (prevents shifted columns) |
| `scripts/to_excel.py` | CSV → Excel import file |
| `scripts/report_html.py` | CSV → Persian HTML review page for reviewers (`python scripts/report_html.py items.csv review.html`) |
| `START.md` | Single-file version of this skill for chats that cannot load folders |
