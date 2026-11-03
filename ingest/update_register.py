"""Update data/source_register.csv without editing the CSV by hand.

Run from the legal-aid-assistant folder:
    python ingest/update_register.py

Safe to run more than once: it updates rows by doc_id and adds missing ones.
"""
import csv
from pathlib import Path

REGISTER = Path("data/source_register.csv")

# doc_id -> fields to change on an existing row
UPDATES = {
    "police_act_2020": {"status": "ok", "notes": "Official Gazette copy"},
    "legal_aid_act_2011": {
        "status": "bill_text_verify",
        "notes": "Copy is labelled A BILL; replace with gazetted Act",
    },
    "vapp_act_2015": {
        "status": "excluded_scanned_only",
        "notes": "Only scanned copies found; scan kept in data/excluded/",
    },
}

# rows to add if they are not already there
NEW_ROWS = [
    {
        "doc_id": "labour_act_cap_l1", "title": "Labour Act (Cap L1)",
        "file": "labour_act_cap_l1.pdf", "problem_area": "employment",
        "doc_type": "statute", "status": "ok", "source_url": "",
        "date_downloaded": "2026-10-30", "canonical": "yes",
        "notes": "Mainly covers manual and clerical workers",
    },
    {
        "doc_id": "employee_compensation_act_2010",
        "title": "Employees' Compensation Act 2010",
        "file": "employee_compensation_act_2010.pdf",
        "problem_area": "employment", "doc_type": "statute", "status": "ok",
        "source_url": "", "date_downloaded": "2026-10-30", "canonical": "yes",
        "notes": "Official Gazette copy",
    },
]


def main():
    with open(REGISTER, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    by_id = {r["doc_id"]: r for r in rows}
    for doc_id, changes in UPDATES.items():
        if doc_id in by_id:
            by_id[doc_id].update(changes)
            print("updated:", doc_id)
        else:
            print("NOT FOUND (skipped):", doc_id)

    for new in NEW_ROWS:
        if new["doc_id"] in by_id:
            print("already there:", new["doc_id"])
        else:
            rows.append({k: new.get(k, "") for k in fields})
            print("added:", new["doc_id"])

    with open(REGISTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Done. {len(rows)} rows in {REGISTER}")


if __name__ == "__main__":
    main()
