# Examples

`examples/sample_items.csv` contains seven complete, valid rows. `examples/bad_items.csv`
shows typical mistakes; run `python scripts/validate.py examples/bad_items.csv` to see them caught.

## A good term

| Column | Value |
| --- | --- |
| item_id | T0142 |
| type | term |
| text | tachycardia |
| ipa | /ˌtækɪˈkɑːrdiə/ |
| meaning_fa | تاکی‌کاردی، تندضربانی قلب |
| clinical_fa | تاکی‌کاردی |
| definition_en | A heart rate faster than normal, usually over 100 beats per minute in adults. |
| note_fa | متضادش bradycardia است. |
| parts | W0012+W0003+W0040 (tachy- + cardi/o + -ia) |
| example_en | The patient developed tachycardia after the fever started. |
| example_fa | بیمار پس از شروع تب دچار تاکی‌کاردی شد. |
| category / body_system | علامت و نشانه / قلب و عروق |
| level / difficulty / specialty | 1 / 2 / common |
| source / license | Stedman's Medical Dictionary — verify / team |
| generated_by | your model name |
| review_flags | IPA;numbers |

Why it is good: the definition does not repeat the term, the example gives clinical context,
the parts exist in `data/word_parts.csv`, and the clinical number (100) is flagged.

## A good new word part

| Column | Value |
| --- | --- |
| item_id | W0068 (next free number) |
| type | prefix |
| text | macro- |
| meaning_fa | بزرگ |
| definition_en | large; abnormally large |
| note_fa | ریشه یونانی؛ مثل macrocyte. |
| category | جزء واژه |
| level / difficulty / specialty | 1 / 1 / common |
| review_flags | new_part |

## A good abbreviation

| Column | Value |
| --- | --- |
| item_id | A0001 |
| type | abbreviation |
| text | BP |
| expansion | blood pressure |
| meaning_fa | فشار خون |
| definition_en | The force of circulating blood against the walls of the arteries. |
| example_en | The nurse checked the patient's BP every four hours. |
| example_fa | پرستار هر چهار ساعت فشار خون بیمار را کنترل کرد. |

## Bad → good

| Problem | Bad | Good |
| --- | --- | --- |
| Term in its own definition | Tachycardia is a fast heart rate. | A heart rate faster than normal, usually over 100 beats per minute in adults. |
| Example without context | He has tachycardia. | The patient developed tachycardia after the fever started. |
| Arabic letters | تاكي‌كاردي | تاکی‌کاردی |
| IPA without slashes or stress | tækɪkɑːrdiə | /ˌtækɪˈkɑːrdiə/ |
| Duplicate word part | new row `W0070 cardi/o` | reuse `W0003` |
| Wrong ID letter | `W0142` for a term | `T0142` |
| Reviewer column filled | medical_reviewer = Dr. X | leave empty |
| Persian meaning too vague | ضربان | تاکی‌کاردی، تندضربانی قلب |
| Value in the wrong column | `W0068,root,capn/o,دی‌اکسید کربن,,,دی‌اکسید کربن` (meaning typed into `variants`) | `W0068,root,capn/o,,,,دی‌اکسید کربن` |
| Loose diagnostic criterion | A smoker with a productive cough for three months was diagnosed with chronic bronchitis. | A long-term smoker with a productive cough on most days was diagnosed with chronic bronchitis. (flag: `claim`) |
| Parts that do not match the spelling | bronchiectasis = `W0035` (bronch/o) + `W0069` | bronchiectasis = `W0074` (bronchi/o) + `W0069` (-ectasis) |
