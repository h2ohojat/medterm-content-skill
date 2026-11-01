#!/usr/bin/env python3
"""Validate MedTerm content drafts against the content style guide.

Usage:
    python scripts/validate.py items.csv
    python scripts/validate.py items.csv --out checked.csv   # also write a normalised copy
    python scripts/validate.py items.csv --json              # machine-readable report

Exit code 0 = no errors (warnings allowed), 1 = errors found, 2 = could not read input.
Standard library only, so it runs in any sandbox that has Python 3.8+.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COLUMNS = [
    "item_id", "type", "text", "variants", "plural", "ipa", "meaning_fa", "approved_fa",
    "clinical_fa", "definition_en", "note_fa", "parts", "example_en", "example_fa",
    "category", "body_system", "level", "difficulty", "specialty", "mnemonic", "ref_id",
    "source", "license", "audio_status", "medical_reviewer", "language_reviewer",
    "expansion", "generated_by", "review_flags",
]
REQUIRED = ["item_id", "type", "text", "meaning_fa", "definition_en", "category",
            "level", "difficulty", "specialty", "source", "license"]
TYPES = {"term", "prefix", "root", "suffix", "abbreviation"}
ID_LETTER = {"term": "T", "prefix": "W", "root": "W", "suffix": "W", "abbreviation": "A"}
PART_TYPES = {"prefix", "root", "suffix"}

CATEGORIES = {
    "anatomy": "آناتومی", "sign_symptom": "علامت و نشانه", "disease": "بیماری",
    "diagnostic_procedure": "روش تشخیصی", "lab_test": "آزمایش",
    "treatment_surgery": "درمان و جراحی", "hospital_general": "اصطلاح عمومی بیمارستان",
    "word_part": "جزء واژه",
}
BODY_SYSTEMS = {
    "cardiovascular": "قلب و عروق", "respiratory": "تنفس", "digestive": "گوارش",
    "nervous": "عصبی", "musculoskeletal": "اسکلتی-عضلانی", "urinary": "ادراری",
    "reproductive": "تولیدمثل", "endocrine": "غدد درون‌ریز", "integumentary": "پوششی",
    "hematologic": "خون", "immune": "ایمنی", "general": "عمومی",
}
SPECIALTIES = {
    "common", "medicine", "nursing", "pharmacy", "dentistry", "midwifery", "laboratory",
    "anesthesia", "operating_room", "emergency", "radiology", "physiotherapy", "nutrition",
    "public_health",
}
LICENSES = {
    "team": "team", "تألیف تیم": "team", "cc by": "CC BY", "cc by-sa": "CC BY-SA",
    "public domain": "public domain", "مالکیت عمومی": "public domain",
    "purchased": "purchased", "خریداری‌شده": "purchased",
}
REVIEWER_COLUMNS = ["audio_status", "medical_reviewer", "language_reviewer"]
PERSIAN_COLUMNS = ["meaning_fa", "approved_fa", "clinical_fa", "note_fa", "example_fa"]
ENGLISH_COLUMNS = ["text", "variants", "plural", "ipa", "definition_en", "parts", "example_en",
                   "level", "difficulty", "specialty", "ref_id", "expansion"]

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
ARABIC_LETTERS = re.compile("[يك]")
PERSIAN_LETTER = re.compile("[؀-ۿ]")
LATIN_DIGIT = re.compile("[0-9]")
ANY_DIGIT = re.compile("[0-9۰-۹٠-٩]")
# clinical numbers written as words or with units (the digit check alone missed "three months")
NUMBER_WORDS = re.compile(
    r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|"
    r"sixty|seventy|eighty|ninety|hundred|thousand|twice|percent|mmhg|mg|mcg|ml|bpm|kg|mmol|"
    r"seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b", re.I)
PERSIAN_NUMBER_WORDS = re.compile(  # whole words only: «سال» but not «بزرگسالی»
    r"(?<![؀-ۿ‌])(درصد|میلی‌گرم|میلی‌لیتر|میلی‌متر جیوه|ماه|سال|ساعت|دقیقه)(?![؀-ۿ‌])")
# clinical claims in example sentences: causes, diagnosis, frequency, risk
CLAIM_WORDS = re.compile(
    r"\b(diagnos\w*|criteri\w*|always|never|most (common|important|frequent)|leading cause|"
    r"risk factors?|causes?|caused|can lead to|leads? to|usually|typically|first-line|"
    r"treatment of choice|indicates?|confirms?)\b", re.I)
ID_PATTERN = re.compile(r"^[TWA]\d{4}$")
PARTS_PATTERN = re.compile(r"^W\d{4}(\+W\d{4})*$")

# messages are Persian: the writer reads them; field names stay English
ERROR, WARNING = "error", "warning"


def words(s):
    return [w for w in re.split(r"\s+", s.strip()) if w]


def bare(text):
    """Word-part text without hyphens and combining vowel: 'cardi/o' -> 'cardi'."""
    return text.strip("-").split("/")[0].lower()


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in reader]
        return reader.fieldnames or [], rows


def field_counts(path):
    """Number of fields in each data row (row 2 onwards), to catch shifted or missing columns."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [len(r) for r in list(csv.reader(f))[1:] if any(c.strip() for c in r)]


def load_reference():
    parts = {}
    p = ROOT / "data" / "word_parts.csv"
    if p.exists():
        for r in read_csv(p)[1]:
            parts[r["item_id"]] = r
    glossary = {}
    g = ROOT / "data" / "glossary_fa.csv"
    if g.exists():
        for r in read_csv(g)[1]:
            glossary[r["english"].lower()] = r
    return parts, glossary


def normalise(row):
    """Safe automatic fixes: digits in numeric fields, canonical category/system/licence values.
    Arabic letters are reported as errors and only fixed in the --out copy."""
    for c in ("level", "difficulty"):
        row[c] = row.get(c, "").translate(PERSIAN_DIGITS)
    cat = row.get("category", "")
    row["category"] = CATEGORIES.get(cat, cat)
    bs = row.get("body_system", "")
    row["body_system"] = BODY_SYSTEMS.get(bs, bs)
    lic = row.get("license", "")
    row["license"] = LICENSES.get(lic.lower(), lic)
    return row


def check(rows, header, parts_ref, glossary, existing_ids, counts=None):
    issues = []

    def add(row_no, item, level, field, msg):
        issues.append({"row": row_no, "item_id": item, "level": level, "field": field, "message": msg})

    missing = [c for c in REQUIRED if c not in header]
    if missing:
        add(0, "", ERROR, "header", "ستون‌های اجباری وجود ندارند: " + ", ".join(missing))
    unknown = [c for c in header if c and c not in COLUMNS]
    if unknown:
        add(0, "", WARNING, "header", "ستون‌های ناشناخته (نادیده گرفته می‌شوند): " + ", ".join(unknown))
    for i, n in enumerate(counts or [], start=2):
        if n != len(header):
            iid = rows[i - 2].get("item_id", "") if i - 2 < len(rows) else ""
            add(i, iid, ERROR, "columns",
                f"این ردیف {n} ستون دارد ولی سرستون {len(header)} ستون؛ مقدارها جابه‌جا شده‌اند.")

    batch_ids = {}
    batch_texts = {}
    batch_parts = {r.get("item_id", ""): r for r in rows if r.get("type") in PART_TYPES}
    known_part_ids = set(parts_ref) | set(batch_parts)
    known_texts = {r["text"].lower(): r["item_id"] for r in parts_ref.values()}
    prefixes = [bare(r["text"]) for r in list(parts_ref.values()) + list(batch_parts.values())
                if r.get("type") == "prefix" and len(bare(r["text"])) > 2]
    suffixes = [bare(r["text"]) for r in list(parts_ref.values()) + list(batch_parts.values())
                if r.get("type") == "suffix" and len(bare(r["text"])) > 2]

    for i, raw in enumerate(rows, start=2):  # row 1 is the header
        r = dict(raw)
        iid, typ, text = r.get("item_id", ""), r.get("type", ""), r.get("text", "")
        level_raw = r.get("level", "").translate(PERSIAN_DIGITS)
        flags = [f.strip() for f in r.get("review_flags", "").split(";") if f.strip()]

        def err(field, msg):
            add(i, iid, ERROR, field, msg)

        def warn(field, msg):
            add(i, iid, WARNING, field, msg)

        for c in REQUIRED:
            if c in header and not r.get(c):
                err(c, "خالی است؛ این ستون اجباری است.")

        # type and id
        if typ and typ not in TYPES:
            err("type", f"«{typ}» مجاز نیست؛ یکی از: " + "، ".join(sorted(TYPES)))
        if iid:
            if not ID_PATTERN.match(iid):
                err("item_id", "قالب باید یک حرف (T/W/A) و چهار رقم باشد، مثل T0142.")
            elif typ in ID_LETTER and iid[0] != ID_LETTER[typ]:
                err("item_id", f"برای نوع {typ} باید با حرف {ID_LETTER[typ]} شروع شود.")
            if iid in batch_ids:
                err("item_id", f"تکراری است؛ در سطر {batch_ids[iid]} هم آمده.")
            batch_ids.setdefault(iid, i)
            if iid in parts_ref and parts_ref[iid]["text"].lower() != text.lower():
                err("item_id", f"این شناسه قبلاً برای «{parts_ref[iid]['text']}» ثبت شده است.")
            if iid in existing_ids and iid not in parts_ref:
                err("item_id", "این شناسه قبلاً در فایل اصطلاحات موجود ثبت شده است.")

        # text format by type
        if text:
            key = text.lower()
            if key in batch_texts:
                err("text", f"تکراری است؛ در سطر {batch_texts[key]} هم آمده.")
            batch_texts.setdefault(key, i)
            if typ in PART_TYPES and key in known_texts and known_texts[key] != iid:
                err("text", f"این جزء واژه قبلاً با شناسه {known_texts[key]} وجود دارد؛ از همان استفاده کنید.")
            if typ == "prefix" and not (text.endswith("-") and not text.startswith("-")):
                err("text", "پیشوند باید با خط تیره تمام شود، مثل tachy-")
            if typ == "suffix" and not (text.startswith("-") and not text.endswith("-")):
                err("text", "پسوند باید با خط تیره شروع شود، مثل -itis")
            if typ == "root" and "/" not in text:
                warn("text", "ریشه معمولاً با شکل ترکیبی نوشته می‌شود، مثل cardi/o")
            if typ == "term" and text != text.lower():
                warn("text", "اصطلاح با حروف کوچک نوشته می‌شود، مگر نام خاص باشد.")
            if PERSIAN_LETTER.search(text):
                err("text", "متن اصطلاح باید انگلیسی باشد.")

        # pronunciation
        ipa = r.get("ipa", "")
        if typ == "term":
            if not ipa:
                err("ipa", "برای اصطلاح، آوانگاری اجباری است.")
            elif not (ipa.startswith("/") and ipa.endswith("/") and len(ipa) > 2):
                err("ipa", "آوانگاری باید بین دو خط مورب باشد، مثل /ˌtækɪˈkɑːrdiə/")
            elif "ˈ" not in ipa and len(re.findall("[aeiouæɑɒɔəɛɪʊʌ]", ipa)) > 1:
                err("ipa", "تکیه اصلی (ˈ) مشخص نشده است.")
            if "IPA" not in flags:
                flags.append("IPA")

        # English-only fields (catches values pasted into the wrong column)
        for c in ENGLISH_COLUMNS:
            if PERSIAN_LETTER.search(r.get(c, "")) and c not in ("text", "definition_en"):
                err(c, "این ستون فقط انگلیسی است؛ احتمالاً مقدار در ستون اشتباه آمده.")

        # Persian fields
        for c in PERSIAN_COLUMNS:
            v = r.get(c, "")
            if ARABIC_LETTERS.search(v):
                err(c, "حرف «ي» یا «ك» عربی دارد؛ از «ی» و «ک» فارسی استفاده کنید.")
            if v and LATIN_DIGIT.search(v):
                warn(c, "در متن فارسی از ارقام فارسی استفاده کنید (۱۰۰ نه 100).")
        mfa = r.get("meaning_fa", "")
        if mfa:
            if not PERSIAN_LETTER.search(mfa):
                err("meaning_fa", "معنی فارسی باید به فارسی باشد.")
            n = len(words(mfa))
            if n > 6:
                err("meaning_fa", f"{n} کلمه است؛ حداکثر ۶ کلمه.")
            g = glossary.get(text.lower())
            approved = g is not None and g.get("status", "") == "approved" and g.get("meaning_fa", "") == mfa
            if typ in ("term", "abbreviation") and not approved:
                if "meaning_fa" not in flags:
                    flags.append("meaning_fa")
                if g is not None and g.get("meaning_fa", "") != mfa:
                    warn("meaning_fa", f"با واژه‌نامه تیم فرق دارد: «{g.get('meaning_fa', '')}»")

        # the Persian example should use the same equivalent as meaning_fa / clinical_fa
        exfa = r.get("example_fa", "")
        if typ == "term" and exfa and mfa:
            forms = [r.get("clinical_fa", ""), r.get("approved_fa", ""), mfa.split("،")[0], text]
            if not any(f.strip() and f.strip() in exfa for f in forms):
                warn("example_fa", "ترجمه مثال، معادل فارسی ثبت‌شده برای این اصطلاح را به کار نبرده است.")

        # word parts need their origin and an example in note_fa (style guide §3)
        if typ in PART_TYPES and not re.search("یونانی|لاتین", r.get("note_fa", "")):
            warn("note_fa", "برای جزء واژه، ریشه (یونانی یا لاتین) و یک اصطلاح نمونه را در note_fa بنویسید.")

        # English definition
        dfn = r.get("definition_en", "")
        if dfn:
            limit = 30 if level_raw == "3" else 20
            n = len(words(dfn))
            if n > limit:
                err("definition_en", f"{n} کلمه است؛ حداکثر {limit} کلمه برای این سطح.")
            if len(re.findall(r"[.!?](\s|$)", dfn)) > 1:
                warn("definition_en", "باید یک جمله باشد.")
            if typ in ("term", "abbreviation") and text and re.search(
                    r"\b" + re.escape(text.lower()) + r"\b", dfn.lower()):
                err("definition_en", "خود اصطلاح نباید در تعریف بیاید.")
            if PERSIAN_LETTER.search(dfn):
                err("definition_en", "تعریف باید انگلیسی باشد.")

        # example sentence
        ex = r.get("example_en", "")
        if typ in ("term", "abbreviation"):
            if not ex:
                err("example_en", "جمله مثال اجباری است.")
            else:
                n = len(words(ex))
                if not 8 <= n <= 20:
                    err("example_en", f"{n} کلمه است؛ باید بین ۸ تا ۲۰ کلمه باشد.")
                forms = [text] + [v.strip() for v in r.get("variants", "").split(",") if v.strip()]
                if r.get("plural"):
                    forms.append(r["plural"])
                if not any(f.lower() in ex.lower() for f in forms if f):
                    err("example_en", "جمله مثال باید خود اصطلاح را داشته باشد.")
            if not r.get("example_fa"):
                err("example_fa", "ترجمه جمله مثال اجباری است.")

        # abbreviation
        if typ == "abbreviation" and not r.get("expansion"):
            err("expansion", "برای اختصار، شکل کامل اجباری است.")

        # word parts
        parts = r.get("parts", "")
        if parts:
            if typ != "term":
                err("parts", "فقط اصطلاح‌ها اجزای واژه دارند.")
            elif not PARTS_PATTERN.match(parts):
                err("parts", "قالب باید شناسه‌ها با + باشد، مثل W0012+W0003+W0040")
            else:
                pids = parts.split("+")
                for pid in pids:
                    if pid not in known_part_ids:
                        err("parts", f"جزء {pid} نه در data/word_parts.csv هست نه در همین فایل.")
                # each part's letters should appear in the term, in order (catches wrong IDs)
                if all(p in known_part_ids for p in pids) and text:
                    pos, t = 0, text.lower()
                    for pid in pids:
                        src = parts_ref.get(pid) or batch_parts.get(pid)
                        stem = bare(src["text"])
                        found = t.find(stem, pos)
                        if found == -1 and len(stem) > 3:  # allow a dropped final vowel: bronchi- / bronch-
                            found = t.find(stem[:-1], pos)
                        if found == -1:
                            warn("parts", f"جزء «{src['text']}» در «{text}» یا در این ترتیب دیده نمی‌شود؛ شناسه را بررسی کنید.")
                            break
                        pos = found + 1
        elif typ == "term" and text:
            t = text.lower()
            hint = [p for p in prefixes if t.startswith(p)] + [s for s in suffixes if t.endswith(s)]
            if hint:
                warn("parts", "ستون اجزا خالی است، ولی به نظر می‌رسد اصطلاح از اجزای شناخته‌شده ساخته شده.")

        # classification
        cat = r.get("category", "")
        if cat and cat not in CATEGORIES and cat not in CATEGORIES.values():
            err("category", f"«{cat}» مجاز نیست؛ فهرست در reference/columns.md")
        if typ in PART_TYPES and cat and CATEGORIES.get(cat, cat) != CATEGORIES["word_part"]:
            err("category", "دسته جزء واژه باید «جزء واژه» باشد.")
        bs = r.get("body_system", "")
        if bs and bs not in BODY_SYSTEMS and bs not in BODY_SYSTEMS.values():
            err("body_system", f"«{bs}» مجاز نیست؛ فهرست در reference/columns.md")
        if r.get("level") and level_raw not in {"1", "2", "3"}:
            err("level", "باید ۱، ۲ یا ۳ باشد.")
        diff = r.get("difficulty", "").translate(PERSIAN_DIGITS)
        if r.get("difficulty") and diff not in {"1", "2", "3", "4", "5"}:
            err("difficulty", "باید عددی از ۱ تا ۵ باشد.")
        for s in [s.strip() for s in r.get("specialty", "").split("|") if s.strip()]:
            if s not in SPECIALTIES:
                err("specialty", f"«{s}» مجاز نیست؛ فهرست در reference/columns.md")
        lic = r.get("license", "")
        if lic and lic.lower() not in LICENSES:
            err("license", f"«{lic}» مجاز نیست؛ team، CC BY، CC BY-SA، public domain یا purchased")

        # AI drafting rules
        for c in REVIEWER_COLUMNS:
            if r.get(c):
                err(c, "این ستون را فقط بازبین پر می‌کند؛ در پیش‌نویس خالی بگذارید.")
        if not r.get("generated_by"):
            warn("generated_by", "نام مدلی که پیش‌نویس را ساخته ثبت نشده است.")

        # automatic review flags
        en_text = " ".join(r.get(c, "") for c in ("definition_en", "example_en"))
        fa_text = " ".join(r.get(c, "") for c in ("note_fa", "example_fa"))
        if typ in ("term", "abbreviation") and (
                any(ANY_DIGIT.search(r.get(c, "")) for c in ("definition_en", "example_en", "note_fa"))
                or NUMBER_WORDS.search(en_text) or PERSIAN_NUMBER_WORDS.search(fa_text)):
            if "numbers" not in flags:
                flags.append("numbers")
        if typ in ("term", "abbreviation") and CLAIM_WORDS.search(r.get("example_en", "")):
            if "claim" not in flags:
                flags.append("claim")
        if typ in PART_TYPES and iid not in parts_ref and "new_part" not in flags:
            flags.append("new_part")
        raw["review_flags"] = ";".join(flags)

    return issues


def main():
    ap = argparse.ArgumentParser(description="Validate MedTerm content drafts.")
    ap.add_argument("csv", help="CSV file with draft items")
    ap.add_argument("--existing", help="CSV of items already in the system (duplicate IDs)")
    ap.add_argument("--out", help="write a normalised copy with review flags filled in")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        header, rows = read_csv(args.csv)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        print(f"Could not read {args.csv}: {e}", file=sys.stderr)
        return 2

    parts_ref, glossary = load_reference()
    existing_ids = set()
    if args.existing:
        existing_ids = {r.get("item_id", "") for r in read_csv(args.existing)[1]}

    rows = [normalise(r) for r in rows]
    issues = check(rows, header, parts_ref, glossary, existing_ids, field_counts(args.csv))
    errors = [x for x in issues if x["level"] == ERROR]
    warnings = [x for x in issues if x["level"] == WARNING]

    if args.out:
        with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                out = {c: r.get(c, "") for c in COLUMNS}
                for c in PERSIAN_COLUMNS:
                    out[c] = out[c].replace("ي", "ی").replace("ك", "ک")
                w.writerow(out)

    if args.json:
        print(json.dumps({"items": len(rows), "errors": len(errors), "warnings": len(warnings),
                          "issues": issues,
                          "review_flags": {r.get("item_id", ""): r.get("review_flags", "") for r in rows}},
                         ensure_ascii=False, indent=2))
    else:
        print(f"{len(rows)} items · {len(errors)} errors · {len(warnings)} warnings")
        for x in issues:
            mark = "ERROR  " if x["level"] == ERROR else "warning"
            print(f"  [{mark}] row {x['row']} {x['item_id'] or '-'} · {x['field']}: {x['message']}")
        print("\nreview_flags:")
        for r in rows:
            if r.get("review_flags"):
                print(f"  {r.get('item_id', '-')}: {r['review_flags']}")
        if not errors:
            print("\nOK — no errors. Drafts still need medical and language review before publishing.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
