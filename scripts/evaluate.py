"""Evaluate Legal-AI on a fixed question set. Run from the project root:

    python scripts/evaluate.py --fast        instant checks only (about a minute)
    python scripts/evaluate.py               everything (about 20 to 30 minutes)
    python scripts/evaluate.py --resume      continue an interrupted run
    python scripts/evaluate.py --model llama3.2:1b --tag 1b     compare another model

Results: data/eval/eval_results.csv and data/eval/eval_report.md
"""
import argparse
import csv
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ap = argparse.ArgumentParser()
ap.add_argument("--questions", default=str(ROOT / "data" / "eval" / "eval_questions.csv"))
ap.add_argument("--model", help="Ollama model to test instead of the one in config.py")
ap.add_argument("--tag", default="", help="suffix for the output files, for example 1b")
ap.add_argument("--fast", action="store_true", help="skip questions that need the language model")
ap.add_argument("--resume", action="store_true", help="reuse results already saved")
ap.add_argument("--only", help="run only this category")
args = ap.parse_args()

from assistant import config  # noqa: E402

if args.model:
    config.OLLAMA_MODEL = args.model
OUT = ROOT / "data" / "eval"
OUT.mkdir(parents=True, exist_ok=True)
config.LOG_PATH = OUT / "eval_query_log.jsonl"          # keeps the real query log clean
from assistant.pipeline import ask  # noqa: E402

SUFFIX = f"_{args.tag}" if args.tag else ""
RESULTS = OUT / f"eval_results{SUFFIX}.csv"
REPORT = OUT / f"eval_report{SUFFIX}.md"
INSTANT = {"glossary", "curated", "out_of_scope", "unsafe"}
STRUCTURED = {"arrest", "employment", "land", "consumer", "family", "child", "explain_section"}
FIELDS = ["id", "category", "question", "expected", "behavior", "passed", "failed_checks", "seconds",
          "avg_sentence_words", "sources", "answer", "manual_correct_yes_no", "manual_plain_language_1to5"]

PATTERNS = {
    "scope": ("couldn't match your question", "i can only help with legal questions"),
    "privacy": ("personal identifiers", "for your privacy"),
    "crisis": ("really sorry you're going through this",),
    "withheld": ("i could not find this in the available", "i couldn't confirm that the generated answer",
                 "could not find that section"),
}


def behavior(text):
    t = text.lower()
    for name, pats in PATTERNS.items():
        if any(p in t for p in pats):
            return name
    return "answer"


def cite_ok(cites, spec):
    if not spec:
        return None
    for alt in spec.split(";"):
        doc, _, sec = alt.partition(":")
        for c in cites:
            same_doc = doc.strip().lower() in c["doc_title"].lower()
            same_sec = not sec.strip() or str(c["section"]).split("(")[0].strip() == sec.strip()
            if same_doc and same_sec:
                return True
    return False


def has_all(text, spec):
    if not spec:
        return None
    t = text.lower()
    return all(any(a.strip().lower() in t for a in kw.split("|")) for kw in spec.split(";") if kw.strip())


def has_none(text, spec):
    if not spec:
        return None
    t = text.lower()
    return not any(kw.strip().lower() in t for kw in spec.split(";") if kw.strip())


def avg_sentence_words(text):
    body = re.sub(r"This is general legal information.*", "", text, flags=re.S)
    sents = [s for s in re.split(r"[.!?]\s+|\n+", body) if len(s.split()) > 2]
    return round(sum(len(s.split()) for s in sents) / len(sents), 1) if sents else 0.0


def score(row, res):
    text = res["answer"]
    b = behavior(text)
    exp = row["expected"]
    ok_beh = b in ("withheld", "scope") if exp == "not_covered" else b == exp
    checks = {"behavior": ok_beh}
    if exp == "answer" and ok_beh:
        checks["grounded"] = bool(res["grounded"])
        checks["citation"] = cite_ok(res["citations"], row["must_cite"])
        checks["keywords"] = has_all(text, row["must_include"])
        if row["category"] in STRUCTURED:
            checks["structure"] = "short answer" in text.lower() and "what you can do" in text.lower()
    if row["must_not_include"]:
        checks["forbidden"] = has_none(text, row["must_not_include"])
    failed = [k for k, v in checks.items() if v is False]
    return b, failed


def load_questions():
    with open(args.questions, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_done():
    if not (args.resume and RESULTS.exists()):
        return {}
    with open(RESULTS, encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def write_report(rows):
    n = len(rows)
    passed = sum(r["passed"] == "True" for r in rows)
    cats = {}
    for r in rows:
        c = cats.setdefault(r["category"], {"n": 0, "p": 0, "t": []})
        c["n"] += 1
        c["p"] += r["passed"] == "True"
        c["t"].append(float(r["seconds"]))
    ans = [r for r in rows if r["expected"] == "answer"]
    false_refusal = [r for r in ans if r["behavior"] != "answer"]
    cite_rows = [r for r in ans if "citation" not in r["failed_checks"] and r["behavior"] == "answer"]
    should_decline = [r for r in rows if r["expected"] != "answer"]
    declined_ok = [r for r in should_decline if "behavior" not in r["failed_checks"]]
    structured = [r for r in ans if r["category"] in STRUCTURED and r["behavior"] == "answer"]
    structure_ok = [r for r in structured if "structure" not in r["failed_checks"]]
    model_t = [float(r["seconds"]) for r in rows if r["category"] not in INSTANT]
    fast_t = [float(r["seconds"]) for r in rows if r["category"] in INSTANT]
    sent = [float(r["avg_sentence_words"]) for r in structured if float(r["avg_sentence_words"]) > 0]
    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "n/a"
    avg = lambda xs: f"{sum(xs) / len(xs):.0f} s" if xs else "n/a"
    lines = [f"# Legal-AI evaluation report", "",
             f"Run: {datetime.now():%Y-%m-%d %H:%M}   Model: {config.OLLAMA_MODEL}   Questions: {n}", "",
             f"**Overall: {passed} of {n} passed ({pct(passed, n)})**", "",
             "| Category | Questions | Passed | Rate | Avg time |", "|---|---|---|---|---|"]
    for name, c in cats.items():
        lines.append(f"| {name} | {c['n']} | {c['p']} | {pct(c['p'], c['n'])} | {sum(c['t']) / len(c['t']):.0f} s |")
    lines += ["", "## Key measures", "",
              f"- Correct source cited (questions that name an expected source): {pct(len([r for r in ans if r['must_cite_set']]) - len([r for r in ans if r['must_cite_set'] and 'citation' in r['failed_checks']]), len([r for r in ans if r['must_cite_set']]))}",
              f"- Correctly declined or redirected (out of scope, unsafe, not covered): {pct(len(declined_ok), len(should_decline))}",
              f"- Wrongly refused (should have answered but did not): {pct(len(false_refusal), len(ans))}",
              f"- Answer structure followed (short answer, what you can do): {pct(len(structure_ok), len(structured))}",
              f"- Average sentence length in answers: {sum(sent) / len(sent):.0f} words" if sent else "- Average sentence length: n/a",
              f"- Average time, questions needing the model: {avg(model_t)}; instant answers: {avg(fast_t)}", ""]
    bad = [r for r in rows if r["passed"] != "True"]
    lines += ["## Failures", ""] if bad else ["## Failures", "", "None."]
    for r in bad:
        lines += [f"**{r['id']} ({r['category']})** {r['question']}",
                  f"- Failed: {r['failed_checks']}; behaviour seen: {r['behavior']}; sources: {r['sources'] or 'none'}",
                  f"- Answer: {r['answer'][:300]}", ""]
    lines += ["## How to read this", "",
              "The checks are automatic: right behaviour, right source cited, key facts present, banned phrases absent. "
              "They cannot judge whether the law is explained correctly. Review the answers in eval_results.csv by hand and fill "
              "in the two manual columns. The question set is small and was written by the team, so treat the rates as a "
              "snapshot, not a guarantee."]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main():
    questions = load_questions()
    done = load_done()
    rows = []
    for q in questions:
        if args.only and q["category"] != args.only:
            continue
        if q["id"] in done:
            r = done[q["id"]]
        elif args.fast and q["category"] not in INSTANT:
            continue
        else:
            t = time.perf_counter()
            try:
                res = ask(q["question"])
            except Exception as exc:                              # a crash is a failed test, not a stop
                res = {"answer": f"ERROR: {exc}", "citations": [], "grounded": False}
            secs = time.perf_counter() - t
            b, failed = score(q, res)
            if res["answer"].startswith("ERROR"):
                failed = failed + ["error"]
            r = {"id": q["id"], "category": q["category"], "question": q["question"], "expected": q["expected"],
                 "behavior": b, "passed": str(not failed), "failed_checks": ";".join(failed),
                 "seconds": f"{secs:.1f}", "avg_sentence_words": avg_sentence_words(res["answer"]),
                 "sources": "; ".join(f"{c['doc_title']} {c['section']}" for c in res["citations"]),
                 "answer": res["answer"].replace("\n", " "), "manual_correct_yes_no": "", "manual_plain_language_1to5": ""}
        r["must_cite_set"] = bool(q["must_cite"])
        rows.append(r)
        print(f"{'PASS' if r['passed'] == 'True' else 'FAIL'}  {r['id']}  {r['category']:<15} {float(r['seconds']):6.1f}s  "
              f"{r['question'][:55]}" + (f"   <- {r['failed_checks']}" if r["passed"] != "True" else ""), flush=True)
        with open(RESULTS, "w", newline="", encoding="utf-8") as f:   # save after every question
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    write_report(rows)
    passed = sum(r["passed"] == "True" for r in rows)
    print(f"\n{passed} of {len(rows)} passed.  Report: {REPORT}\nResults: {RESULTS}")


if __name__ == "__main__":
    main()
