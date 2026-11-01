# CSV columns and allowed values

Output columns **in this exact order**. Every row has exactly 29 fields; an empty cell is still
written as an empty field between two commas. If you can run Python, write a JSON list with these
keys and convert it with `scripts/json_to_csv.py` instead of typing CSV. All 29 columns match the project's bulk-import specification
(content style guide §9.1; SRS FR-314 and CR-011). The last three are `expansion`, `generated_by` and `review_flags`.

| # | Column | Required | Notes |
| --- | --- | --- | --- |
| 1 | `item_id` | always | `T####` term, `W####` word part, `A####` abbreviation |
| 2 | `type` | always | `term`, `prefix`, `root`, `suffix`, `abbreviation` |
| 3 | `text` | always | see style guide §2 |
| 4 | `variants` | no | other accepted spellings, comma-separated (quote the field) |
| 5 | `plural` | no | irregular plural only |
| 6 | `ipa` | terms | `/ˈ…/` |
| 7 | `meaning_fa` | always | 1–6 Persian words |
| 8 | `approved_fa` | no | Academy-approved equivalent |
| 9 | `clinical_fa` | no | clinical usage, if different |
| 10 | `definition_en` | always | one sentence, word limit by level |
| 11 | `note_fa` | no | ≤ 2 sentences |
| 12 | `parts` | if the term has structure | word-part IDs joined with `+`, e.g. `W0012+W0003+W0040` |
| 13 | `example_en` | terms, abbreviations | 8–20 words, contains the term |
| 14 | `example_fa` | terms, abbreviations | fluent translation |
| 15 | `category` | always | see below |
| 16 | `body_system` | if relevant | see below |
| 17 | `level` | always | `1`, `2`, `3` |
| 18 | `difficulty` | always | `1`–`5` |
| 19 | `specialty` | always | see below; several separated by `|` |
| 20 | `mnemonic` | no | must not distort the meaning |
| 21 | `ref_id` | no | UMLS CUI or MeSH ID, only if you are certain |
| 22 | `source` | always | reference to verify against |
| 23 | `license` | always | see below |
| 24 | `audio_status` | **leave empty** | filled by the language reviewer |
| 25 | `medical_reviewer` | **leave empty** | filled by the reviewer |
| 26 | `language_reviewer` | **leave empty** | filled by the reviewer |
| 27 | `expansion` | abbreviations | full form, e.g. `blood pressure` |
| 28 | `generated_by` | AI drafts | your model name |
| 29 | `review_flags` | AI drafts | style guide §4, separated by `;` |

## Allowed values

Persian or English values are both accepted; use the Persian value in output.

### `category`
| English key | Persian |
| --- | --- |
| `anatomy` | آناتومی |
| `sign_symptom` | علامت و نشانه |
| `disease` | بیماری |
| `diagnostic_procedure` | روش تشخیصی |
| `lab_test` | آزمایش |
| `treatment_surgery` | درمان و جراحی |
| `hospital_general` | اصطلاح عمومی بیمارستان |
| `word_part` | جزء واژه |

Word parts always use `جزء واژه`.

### `body_system`
| English key | Persian |
| --- | --- |
| `cardiovascular` | قلب و عروق |
| `respiratory` | تنفس |
| `digestive` | گوارش |
| `nervous` | عصبی |
| `musculoskeletal` | اسکلتی-عضلانی |
| `urinary` | ادراری |
| `reproductive` | تولیدمثل |
| `endocrine` | غدد درون‌ریز |
| `integumentary` | پوششی |
| `hematologic` | خون |
| `immune` | ایمنی |
| `general` | عمومی |

### `specialty`
`common`, `medicine`, `nursing`, `pharmacy`, `dentistry`, `midwifery`, `laboratory`, `anesthesia`, `operating_room`, `emergency`, `radiology`, `physiotherapy`, `nutrition`, `public_health`

### `license`
`team` (تألیف تیم), `CC BY`, `CC BY-SA`, `public domain` (مالکیت عمومی), `purchased` (خریداری‌شده)

### `origin` (word parts, put in `note_fa` as «ریشه یونانی» or «ریشه لاتین»)
Greek / Latin
