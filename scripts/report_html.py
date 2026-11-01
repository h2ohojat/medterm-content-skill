#!/usr/bin/env python3
"""Build a Persian (RTL) HTML review page for a batch of drafted items.

Usage:
    python scripts/report_html.py items.csv review.html
    python scripts/report_html.py items.csv review.html --notes notes.json

The page shows the validator result, the rules checked, every item with its word parts
and review flags, and (optionally, from notes.json) the review history and fixes made.
Standard library only.
"""
import argparse
import json
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import (ERROR, WARNING, PART_TYPES, check, field_counts,  # noqa: E402
                      load_reference, normalise, read_csv)

TYPE_FA = {"term": "اصطلاح", "prefix": "پیشوند", "root": "ریشه", "suffix": "پسوند",
           "abbreviation": "اختصار"}
FLAG_FA = {
    "IPA": "آوانگاری و تکیه بررسی شود",
    "meaning_fa": "معادل فارسی تازه است؛ در واژه‌نامه تیم نیست",
    "numbers": "عدد بالینی دارد (رقمی یا حرفی)؛ مقدار بررسی شود",
    "claim": "مثال یک ادعای بالینی دارد (علت، تشخیص، عامل خطر)؛ درستی‌اش بررسی شود",
    "new_part": "جزء واژه جدید؛ پیش از افزودن به فهرست تأیید شود",
}
RULES = [
    ("ساختار ردیف", ["columns", "header"], "هر ردیف دقیقاً به تعداد ستون‌های سرستون؛ جابه‌جایی مقدارها را می‌گیرد"),
    ("شناسه و نوع", ["item_id", "type"], "قالب T/W/A و چهار رقم، یکتا بودن، تطابق حرف با نوع"),
    ("شکل نوشتاری", ["text"], "خط تیره پیشوند و پسوند، شکل ترکیبی ریشه، تکراری نبودن جزء واژه"),
    ("آوانگاری", ["ipa"], "بین دو خط مورب، با علامت تکیه اصلی"),
    ("متن فارسی", ["meaning_fa", "approved_fa", "clinical_fa", "note_fa", "example_fa"],
     "۱ تا ۶ کلمه، ی و ک فارسی، ارقام فارسی"),
    ("ستون‌های انگلیسی", ["variants", "plural", "parts", "expansion", "ref_id", "specialty"],
     "بدون حروف فارسی؛ جابه‌جایی ستون را می‌گیرد"),
    ("تعریف انگلیسی", ["definition_en"], "یک جمله، سقف کلمه بر اساس سطح، بدون تکرار خود اصطلاح"),
    ("جمله مثال", ["example_en", "example_fa"], "۸ تا ۲۰ کلمه، شامل خود اصطلاح، ترجمه با همان معادل فارسی"),
    ("اجزای واژه", ["parts", "note_fa"], "شناسه‌ها موجودند، حروفشان به همین ترتیب در اصطلاح هست، ریشه جزء ثبت شده"),
    ("طبقه‌بندی", ["category", "body_system", "level", "difficulty"], "مقادیر مجاز دسته، دستگاه، سطح و دشواری"),
    ("منبع و مجوز", ["source", "license"], "منبع برای بررسی و مجوز مجاز"),
    ("ستون‌های بازبین", ["audio_status", "medical_reviewer", "language_reviewer", "generated_by"],
     "خالی ماندن ستون‌های بازبین و ثبت نام مدل"),
]

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n):
    return str(n).translate(FA_DIGITS)


def flag_html(flag):
    flag = flag.strip()
    if flag.startswith("parts:"):
        label, note = "اجزا", "تقسیم اجزا بررسی شود: " + flag[6:].strip()
    elif flag.startswith("uncertain:"):
        label, note = "نامطمئن", flag[10:].strip()
    else:
        label, note = flag, FLAG_FA.get(flag, flag)
    kind = "flag-new" if flag == "new_part" else "flag"
    return (f'<li class="{kind}"><span class="flag-key" dir="ltr">{escape(label)}</span>'
            f'<span>{escape(note)}</span></li>')


def parts_html(ids, lookup):
    chips = []
    for pid in ids.split("+"):
        p = lookup.get(pid)
        if p is None:
            chips.append(f'<span class="part missing" dir="ltr">{escape(pid)}</span>')
            continue
        meaning = p.get("meaning_fa", "")
        chips.append(
            f'<span class="part"><b dir="ltr">{escape(p["text"])}</b>'
            f'<small>{escape(meaning)}</small></span>')
    return '<span class="plus" aria-hidden="true">+</span>'.join(chips)


def item_html(r, issues, lookup):
    typ = r.get("type", "")
    flags = [f for f in r.get("review_flags", "").split(";") if f.strip()]
    errs = [x for x in issues if x["level"] == ERROR]
    warns = [x for x in issues if x["level"] == WARNING]
    status = ("error", f"{fa(len(errs))} خطا") if errs else \
        ("warn", f"{fa(len(warns))} هشدار") if warns else ("ok", "بدون خطا")
    out = [f'<article class="item" data-type="{escape(typ)}" data-flagged="{1 if flags else 0}" '
           f'data-status="{status[0]}">']
    out.append('<header class="item-head">'
               f'<span class="iid" dir="ltr">{escape(r.get("item_id", ""))}</span>'
               f'<span class="tag">{TYPE_FA.get(typ, escape(typ))}</span>'
               f'<span class="status {status[0]}">{status[1]}</span></header>')
    out.append(f'<h3 class="term" dir="ltr">{escape(r.get("text", ""))}</h3>')
    sub = []
    if r.get("ipa"):
        sub.append(f'<span class="ipa" dir="ltr">{escape(r["ipa"])}</span>')
    if r.get("expansion"):
        sub.append(f'<span class="expansion" dir="ltr">{escape(r["expansion"])}</span>')
    if sub:
        out.append('<div class="sub">' + "".join(sub) + "</div>")
    out.append(f'<p class="meaning">{escape(r.get("meaning_fa", ""))}</p>')
    if r.get("clinical_fa") and r["clinical_fa"] not in r.get("meaning_fa", ""):
        out.append(f'<p class="clinical">اصطلاح بالینی: {escape(r["clinical_fa"])}</p>')
    if r.get("parts"):
        out.append('<div class="parts" dir="ltr">' + parts_html(r["parts"], lookup) + "</div>")

    rows = [("تعریف", f'<span dir="ltr" class="en">{escape(r.get("definition_en", ""))}</span>')]
    if r.get("example_en"):
        rows.append(("مثال", f'<span dir="ltr" class="en">{escape(r["example_en"])}</span>'
                             f'<span class="tr">{escape(r.get("example_fa", ""))}</span>'))
    if r.get("note_fa"):
        rows.append(("یادداشت", escape(r["note_fa"])))
    meta = [r.get("category", ""), r.get("body_system", ""),
            f'سطح {fa(r.get("level", ""))}', f'دشواری {fa(r.get("difficulty", ""))} از ۵']
    rows.append(("طبقه‌بندی", " · ".join(escape(m) for m in meta if m.strip())))
    out.append('<dl class="fields">' + "".join(
        f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in rows) + "</dl>")

    if flags:
        out.append('<div class="flags"><h4>برای بازبین</h4><ul>'
                   + "".join(flag_html(f) for f in flags) + "</ul></div>")
    if issues:
        out.append('<ul class="issues">' + "".join(
            f'<li class="{x["level"]}"><span dir="ltr">{escape(x["field"])}</span> {escape(x["message"])}</li>'
            for x in issues) + "</ul>")
    out.append("</article>")
    return "".join(out)


CSS = """
/* Layout: one reading column; summary strip, review history, rules table, then filterable item cards */
:root {
  --bg: #f3f5f7; --surface: #ffffff; --ink: #18222d; --muted: #5b6876; --line: #d8dee6;
  --accent: #0d6b6e; --accent-soft: #e2f1f0; --ok: #2c7a4b; --ok-soft: #e4f3ea;
  --warn: #9a5b00; --warn-soft: #fbf0dc; --err: #b3261e; --err-soft: #fbe6e4;
  --font-fa: "Vazirmatn", "Noto Sans", Tahoma, sans-serif;
  --font-en: "Noto Sans", "Segoe UI", Arial, sans-serif;
  --font-mono: "Noto Sans Mono", ui-monospace, Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #11161b; --surface: #19212a; --ink: #e5eaf0; --muted: #9aa7b4; --line: #2c3743;
  --accent: #5cc1bd; --accent-soft: #163536; --ok: #6cc596; --ok-soft: #173326;
  --warn: #e6a94e; --warn-soft: #3a2c14; --err: #f1847b; --err-soft: #3c1d1b; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #11161b; --surface: #19212a; --ink: #e5eaf0; --muted: #9aa7b4; --line: #2c3743;
  --accent: #5cc1bd; --accent-soft: #163536; --ok: #6cc596; --ok-soft: #173326;
  --warn: #e6a94e; --warn-soft: #3a2c14; --err: #f1847b; --err-soft: #3c1d1b; color-scheme: dark }
body { background: var(--bg); color: var(--ink); font-family: var(--font-fa); font-size: 15px; line-height: 1.75; }
.wrap { max-width: 980px; margin: 0 auto; padding-block: 32px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 40px; }
h1, h2, h3, h4 { text-wrap: balance; margin: 0; }
h1 { font-size: 1.9rem; font-weight: 800; line-height: 1.3; }
h2 { font-size: 1.25rem; font-weight: 800; }
[dir="ltr"] { font-family: var(--font-en); unicode-bidi: isolate; }
.eyebrow { color: var(--accent); font-weight: 600; font-size: .85rem; }
.lede { color: var(--muted); max-width: 65ch; margin: 8px 0 0; }
section { display: grid; gap: 16px; min-width: 0; }
.summary { display: flex; flex-wrap: wrap; gap: 12px; }
.stat { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 12px 16px;
  display: grid; gap: 2px; min-width: 120px; flex: 1 1 120px; }
.stat b { font-size: 1.5rem; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: .85rem; }
.stat.good b { color: var(--ok); }
.verdict { display: flex; gap: 12px; align-items: center; background: var(--ok-soft); color: var(--ok);
  border-radius: 10px; padding: 12px 16px; font-weight: 600; }
.verdict.bad { background: var(--err-soft); color: var(--err); }
.steps { list-style: none; margin: 0; padding: 0; display: grid; gap: 0; counter-reset: s; }
.steps li { counter-increment: s; display: grid; grid-template-columns: 32px 1fr; gap: 12px; padding-block: 10px;
  border-bottom: 1px dashed var(--line); }
.steps li::before { content: counter(s, persian); width: 28px; height: 28px; border-radius: 50%; display: grid;
  place-items: center; font-weight: 800; font-size: .85rem; background: var(--accent-soft); color: var(--accent); }
.steps li.missed::before { background: var(--warn-soft); color: var(--warn); }
.steps li.found::before { background: var(--err-soft); color: var(--err); }
.steps b { display: block; }
.steps span { color: var(--muted); }
.fixes { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.fix { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; display: grid; gap: 6px; min-width: 0; }
.fix header { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.fix p { margin: 0; }
.fix .label { color: var(--muted); font-size: .85rem; }
.kind { font-size: .8rem; font-weight: 600; padding: 1px 10px; border-radius: 99px; background: var(--warn-soft); color: var(--warn); }
.kind.sci { background: var(--err-soft); color: var(--err); }
.table-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }
table { border-collapse: collapse; width: 100%; min-width: 560px; }
th, td { text-align: right; padding: 10px 14px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-size: .85rem; color: var(--muted); font-weight: 600; }
tr:last-child td { border-bottom: 0; }
.pass { color: var(--ok); font-weight: 600; white-space: nowrap; }
.fail { color: var(--err); font-weight: 600; white-space: nowrap; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.toolbar button { font: inherit; font-size: .9rem; border: 1px solid var(--line); background: var(--surface); color: var(--ink);
  border-radius: 99px; padding: 4px 14px; cursor: pointer; }
.toolbar button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: var(--surface); }
.toolbar button:focus-visible, .toolbar input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.toolbar input { font: inherit; font-size: .9rem; border: 1px solid var(--line); background: var(--surface); color: var(--ink);
  border-radius: 8px; padding: 4px 12px; flex: 1 1 180px; min-width: 0; }
.count { color: var(--muted); font-size: .85rem; }
.items { display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 420px), 1fr)); }
.item { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; display: grid; gap: 8px; align-content: start; min-width: 0; }
.item-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.iid { font-family: var(--font-mono); font-size: .8rem; color: var(--muted); }
.tag { font-size: .8rem; padding: 0 10px; border-radius: 99px; background: var(--accent-soft); color: var(--accent); }
.status { margin-inline-start: auto; font-size: .8rem; font-weight: 600; padding: 0 10px; border-radius: 99px; }
.status.ok { background: var(--ok-soft); color: var(--ok); }
.status.warn { background: var(--warn-soft); color: var(--warn); }
.status.error { background: var(--err-soft); color: var(--err); }
.status.ok::before { content: "✓ "; }
.status.error::before { content: "✕ "; }
.term { font-size: 1.35rem; font-weight: 600; text-align: right; }
.sub { display: flex; gap: 12px; flex-wrap: wrap; color: var(--muted); }
.ipa { font-size: 1rem; }
.meaning { margin: 0; font-weight: 600; font-size: 1.05rem; }
.clinical { margin: 0; color: var(--muted); font-size: .9rem; }
.parts { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: flex-end; }
.part { display: inline-grid; text-align: center; border: 1px solid var(--line); border-radius: 8px; padding: 2px 10px; line-height: 1.4; }
.part b { font-weight: 600; }
.part small { font-family: var(--font-fa); color: var(--muted); direction: rtl; }
.part.missing { border-color: var(--err); color: var(--err); }
.plus { color: var(--muted); }
.fields { margin: 0; display: grid; gap: 6px; }
.fields div { display: grid; grid-template-columns: 72px 1fr; gap: 10px; }
.fields dt { color: var(--muted); font-size: .85rem; padding-top: 2px; }
.fields dd { margin: 0; display: grid; gap: 2px; min-width: 0; overflow-wrap: anywhere; }
.fields .en { text-align: left; }
.fields .tr { color: var(--muted); }
.flags { border-top: 1px dashed var(--line); padding-top: 8px; display: grid; gap: 6px; }
.flags h4 { font-size: .85rem; color: var(--warn); }
.flags ul, .issues { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
.flags li { display: flex; gap: 8px; align-items: baseline; font-size: .9rem; }
.flag-key { font-size: .75rem; font-weight: 600; padding: 0 8px; border-radius: 6px; background: var(--warn-soft); color: var(--warn); white-space: nowrap; }
.flag-new .flag-key { background: var(--accent-soft); color: var(--accent); }
.issues li { font-size: .9rem; border-radius: 6px; padding: 4px 10px; }
.issues li.error { background: var(--err-soft); color: var(--err); }
.issues li.warning { background: var(--warn-soft); color: var(--warn); }
.empty { color: var(--muted); }
footer { color: var(--muted); font-size: .85rem; border-top: 1px solid var(--line); padding-top: 16px; display: grid; gap: 4px; }
footer a { color: var(--accent); }
@media (prefers-reduced-motion: no-preference) { .item { transition: border-color .15s; } .item:hover { border-color: var(--accent); } }
"""

JS = """
(function () {
  var buttons = document.querySelectorAll('.toolbar button');
  var items = document.querySelectorAll('.item');
  var search = document.getElementById('search');
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');
  var mode = 'all';
  function fa(n) { return String(n).replace(/[0-9]/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'[d]; }); }
  function apply() {
    var q = (search.value || '').trim().toLowerCase();
    var shown = 0;
    items.forEach(function (el) {
      var t = el.dataset.type;
      var ok = mode === 'all'
        || (mode === 'term' && t === 'term')
        || (mode === 'part' && (t === 'prefix' || t === 'root' || t === 'suffix'))
        || (mode === 'abbreviation' && t === 'abbreviation')
        || (mode === 'flagged' && el.dataset.flagged === '1')
        || (mode === 'issues' && el.dataset.status !== 'ok');
      if (ok && q) ok = el.textContent.toLowerCase().indexOf(q) !== -1;
      el.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = fa(shown) + ' مورد';
    empty.hidden = shown !== 0;
  }
  buttons.forEach(function (b) {
    b.addEventListener('click', function () {
      mode = b.dataset.mode;
      buttons.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      apply();
    });
  });
  search.addEventListener('input', apply);
  apply();
})();
"""


def main():
    ap = argparse.ArgumentParser(description="Build a Persian HTML review page.")
    ap.add_argument("csv")
    ap.add_argument("out")
    ap.add_argument("--notes", help="JSON with title, batch, date, source, steps, fixes")
    args = ap.parse_args()

    header, rows = read_csv(args.csv)
    rows = [normalise(r) for r in rows]
    parts_ref, glossary = load_reference()
    issues = check(rows, header, parts_ref, glossary, set(), field_counts(args.csv))
    notes = json.loads(Path(args.notes).read_text(encoding="utf-8")) if args.notes else {}

    lookup = {k: {"text": v["text"], "meaning_fa": v.get("meaning_fa", "")} for k, v in parts_ref.items()}
    for r in rows:
        if r.get("type") in PART_TYPES:
            lookup[r["item_id"]] = {"text": r["text"], "meaning_fa": r.get("meaning_fa", "")}

    by_row = {}
    for x in issues:
        by_row.setdefault(x["row"], []).append(x)
    errors = [x for x in issues if x["level"] == ERROR]
    warnings = [x for x in issues if x["level"] == WARNING]
    n_terms = sum(r.get("type") == "term" for r in rows)
    n_parts = sum(r.get("type") in PART_TYPES for r in rows)
    n_abbr = sum(r.get("type") == "abbreviation" for r in rows)
    n_flagged = sum(bool(r.get("review_flags")) for r in rows)
    models = sorted({r.get("generated_by", "") for r in rows if r.get("generated_by")})

    title = notes.get("title", "بازبینی محتوا")
    h = [f"<title>{escape(title)}</title>",
         '<meta name="claude:viewport-fit-sides" content="cover">',
         '<link rel="preconnect" href="https://fonts.googleapis.com">',
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800'
         '&family=Noto+Sans:wght@400;600&family=Noto+Sans+Mono&display=swap">',
         f"<style>{CSS}</style>",
         '<div class="wrap" dir="rtl" lang="fa">']

    h.append('<header style="display:grid;gap:6px">'
             f'<span class="eyebrow">{escape(notes.get("batch", "گزارش بررسی"))}</span>'
             f"<h1>{escape(title)}</h1>"
             '<p class="lede">این صفحه نتیجه بررسی خودکار و بازبینی دستی پیش‌نویس‌های ساخته‌شده با اسکیل MedTerm را نشان می‌دهد. '
             'همه موارد هنوز پیش‌نویس‌اند و پیش از انتشار به تأیید بازبین پزشکی و بازبین زبان نیاز دارند.</p>'
             f'<p class="lede">{escape(notes.get("date", ""))}'
             + (f' · مدل سازنده: <span dir="ltr">{escape(", ".join(models))}</span>' if models else "")
             + "</p></header>")

    # summary
    verdict_ok = not errors
    h.append("<section aria-labelledby=\"s-sum\"><h2 id=\"s-sum\">خلاصه بررسی</h2>")
    h.append(f'<div class="verdict{"" if verdict_ok else " bad"}">'
             + (f"بررسی خودکار: بدون خطا · {fa(len(warnings))} هشدار" if verdict_ok
                else f"بررسی خودکار: {fa(len(errors))} خطا · {fa(len(warnings))} هشدار")
             + "</div>")
    h.append('<div class="summary">'
             f'<div class="stat"><b>{fa(len(rows))}</b><span>کل موارد</span></div>'
             f'<div class="stat"><b>{fa(n_terms)}</b><span>اصطلاح</span></div>'
             f'<div class="stat"><b>{fa(n_parts)}</b><span>جزء واژه</span></div>'
             f'<div class="stat"><b>{fa(n_abbr)}</b><span>اختصار</span></div>'
             f'<div class="stat"><b>{fa(n_flagged)}</b><span>دارای برچسب بازبینی</span></div>'
             "</div></section>")

    # history
    if notes.get("steps"):
        h.append('<section aria-labelledby="s-steps"><h2 id="s-steps">روند بررسی</h2><ol class="steps">')
        for s in notes["steps"]:
            h.append(f'<li class="{escape(s.get("state", "done"))}"><div><b>{escape(s["title"])}</b>'
                     f'<span>{escape(s.get("result", ""))}</span></div></li>')
        h.append("</ol></section>")
    if notes.get("fixes"):
        h.append('<section aria-labelledby="s-fix"><h2 id="s-fix">مشکلات پیداشده و اصلاح‌ها</h2><div class="fixes">')
        for f in notes["fixes"]:
            sci = " sci" if f.get("kind") == "علمی" else ""
            h.append('<article class="fix"><header>'
                     f'<span class="iid" dir="ltr">{escape(f["item"])}</span>'
                     f'<span class="kind{sci}">خطای {escape(f.get("kind", ""))}</span></header>'
                     f'<p>{escape(f["problem"])}</p>'
                     f'<p><span class="label">اصلاح: </span>{escape(f["fix"])}</p>'
                     f'<p class="label">پیدا شده با: {escape(f.get("found_by", ""))}</p></article>')
        h.append("</div></section>")

    if notes.get("skill_updates"):
        h.append('<section aria-labelledby="s-upd"><h2 id="s-upd">'
                 f'{escape(notes.get("skill_updates_title", "به‌روزرسانی اسکیل پس از این بررسی"))}</h2>'
                 '<div class="table-wrap"><table><thead><tr><th>درس از این بررسی</th><th>تغییر در اسکیل</th></tr></thead><tbody>')
        for u in notes["skill_updates"]:
            h.append(f'<tr><td>{escape(u["lesson"])}</td><td>{escape(u["change"])}</td></tr>')
        h.append("</tbody></table></div></section>")

    # rules
    h.append('<section aria-labelledby="s-rules"><h2 id="s-rules">قواعد بررسی‌شده</h2>'
             '<div class="table-wrap"><table><thead><tr><th>قاعده</th><th>چه چیزی بررسی شد</th><th>نتیجه</th></tr></thead><tbody>')
    for name, fields, what in RULES:
        n = sum(1 for x in errors if x["field"] in fields)
        w = sum(1 for x in warnings if x["field"] in fields)
        res = (f'<span class="fail">{fa(n)} خطا</span>' if n else
               f'<span class="fail">{fa(w)} هشدار</span>' if w else
               f'<span class="pass">✓ همه {fa(len(rows))} مورد</span>')
        h.append(f"<tr><td>{name}</td><td>{what}</td><td>{res}</td></tr>")
    h.append("</tbody></table></div>"
             '<p class="lede">بررسی خودکار فقط قالب و قواعد نگارش را می‌سنجد. درستی علمی تعریف‌ها، مثال‌ها و اعداد را فقط بازبین پزشکی تأیید می‌کند.</p>'
             "</section>")

    # items
    h.append('<section aria-labelledby="s-items"><h2 id="s-items">موارد</h2>'
             '<div class="toolbar" role="group" aria-label="فیلتر موارد">'
             '<button type="button" data-mode="all" aria-pressed="true">همه</button>'
             '<button type="button" data-mode="term" aria-pressed="false">اصطلاح</button>'
             '<button type="button" data-mode="part" aria-pressed="false">جزء واژه</button>'
             '<button type="button" data-mode="abbreviation" aria-pressed="false">اختصار</button>'
             '<button type="button" data-mode="flagged" aria-pressed="false">دارای برچسب</button>'
             '<button type="button" data-mode="issues" aria-pressed="false">دارای خطا</button>'
             '<input id="search" type="search" placeholder="جستجو در اصطلاح یا معنی" aria-label="جستجو">'
             '<span class="count" id="count"></span></div>'
             '<p class="empty" id="empty" hidden>موردی با این فیلتر پیدا نشد.</p><div class="items">')
    for i, r in enumerate(rows, start=2):
        h.append(item_html(r, by_row.get(i, []), lookup))
    h.append("</div></section>")

    src = notes.get("source")
    h.append("<footer>")
    if src:
        h.append(f'<span>منبع فهرست اصطلاحات: <a href="{escape(src["url"])}" rel="noopener" target="_blank" dir="ltr">'
                 f'{escape(src["name"])}</a> · مجوز <span dir="ltr">{escape(src.get("license", ""))}</span></span>'
                 f'<span>{escape(src.get("used_for", ""))}</span>')
    h.append("<span>ساخته‌شده با scripts/report_html.py از اسکیل MedTerm Content.</span></footer>")
    h.append(f"</div><script>{JS}</script>")

    Path(args.out).write_text("\n".join(h), encoding="utf-8")
    print(f"wrote {args.out} ({len(rows)} items, {len(errors)} errors, {len(warnings)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
