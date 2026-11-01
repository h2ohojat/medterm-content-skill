# Changelog

## 1.1 — 1405-08-01 (2026-10-23)

Lessons from the first test batch (respiratory system, 11 terms + 6 word parts, source list from
*Building a Medical Terminology Foundation 2e*, CC BY 4.0).

### Validator (`scripts/validate.py`)
- **Row structure:** every row must have as many fields as the header; a shifted value is now an error.
- **English-only columns:** Persian text in `variants`, `plural`, `parts`, `expansion` and similar columns is an error (catches a value typed into the wrong column).
- **Numbers in words:** the `numbers` flag now also fires for written numbers and units ("three months", "every four hours", «ماه»، «درصد»).
- **New `claim` flag:** example sentences stating a cause, diagnosis, risk factor or frequency are flagged for medical review.
- **Parts vs. spelling:** warns when a word part's letters do not appear in the term in order.
- **Persian example consistency:** warns when `example_fa` does not use the term's Persian equivalent.
- **Word-part notes:** warns when a word part's `note_fa` lacks its origin (Greek/Latin).
- **Glossary status:** `meaning_fa` is flagged unless the glossary entry is `approved`.

### New tools
- `scripts/json_to_csv.py` — models with code execution write JSON and convert, so columns cannot shift.
- `scripts/report_html.py` — Persian review page for reviewers (added in 1.0.1).

### Instructions and data
- `SKILL.md`: hard rules 8 (exact columns) and 9 (examples show usage, not diagnostic rules); JSON-first workflow; longer checklist.
- `style-guide.md`, `examples.md`: new flag, four new common mistakes with bad → good examples.
- `data/word_parts.csv`: 74 parts (+ capn/o, -ectasis, atel/o, alveol/o, epiglott/o, -spasm, bronchi/o); new `status` column.
- `data/glossary_fa.csv`: 24 entries (+ 10 respiratory terms); all `needs_review`.

## 1.0 — 1405-08-01

First version: terms, word parts and abbreviations; validator, Excel export, single-file `START.md`.
