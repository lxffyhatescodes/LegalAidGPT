"""Rename and sort the files in data/raw, and draft data/source_register.csv.

Run from the legal-aid-assistant folder:
    python ingest/organise_raw.py            # dry run: only shows what WOULD happen
    python ingest/organise_raw.py --apply    # does it

Nothing is deleted. Unwanted files are moved to data/excluded/ (or docs/).
Matching is by the start of the old file name, so long names still match.
"""
import csv
import shutil
import sys
from pathlib import Path

RAW = Path("data/raw")
EXCLUDED = Path("data/excluded")
DOCS = Path("docs")
REGISTER = Path("data/source_register.csv")
DRAFT = Path("data/source_register_draft.csv")
DOWNLOADED = "2026-10-30"

# (old name starts with, new name, title, problem_area, doc_type, status)
KEEP = [
    ("1999 consitution", "constitution_1999.pdf", "Constitution of the Federal Republic of Nigeria 1999", "all_areas", "statute", "ok"),
    ("2015_Administration_of_Criminal_Justice", "acja_2015.pdf", "Administration of Criminal Justice Act 2015", "arrest", "statute", "ok"),
    ("Police-Act-2020", "police_act_2020.pdf", "Police Act 2020", "arrest", "statute", "needs_ocr"),
    ("FREP Rules", "frep_rules_2009.pdf", "Fundamental Rights (Enforcement Procedure) Rules 2009", "arrest", "rules", "ok"),
    ("land_use_act", "land_use_act_1978.pdf", "Land Use Act 1978 (Cap L5)", "land", "statute", "ok"),
    ("JUDGMENT-pdf2-1", "land_judgment_edo_1.pdf", "Edo State High Court judgment (topic to confirm)", "land", "judgment", "confirm_topic"),
    ("JUDGMENT-SUIT-NO", "esezobor_v_emowele_hcu_33_2018.pdf", "Esezobor v Emowele, HCU/33/2018 (Edo High Court)", "land", "judgment", "confirm_topic"),
    ("JUDGMENTpdf", "land_judgment_edo_3.pdf", "Edo State High Court judgment (topic to confirm)", "land", "judgment", "confirm_topic"),
    ("Nigeria_Tenant_Rights", "tenant_rights_starter_pack.pdf", "Nigeria Tenant Rights Legal Document Starter Pack", "tenant", "guide", "check_author"),
    ("FCCPA-2018", "fccpa_2018.pdf", "Federal Competition and Consumer Protection Act 2018", "consumer", "statute", "ok"),
    ("The-FCCPC-Administrative-Penalties", "fccpc_admin_penalties_regs_2020.pdf", "FCCPC Administrative Penalties Regulations 2020", "consumer", "regulation", "ok"),
    ("cbn_consumer_protection", "cbn_consumer_protection_regs.pdf", "CBN Consumer Protection Regulations", "consumer", "regulation", "ok"),
    ("DEON-Consumer-Lending", "deon_consumer_lending_guidelines_2025.pdf", "DEON Consumer Lending Guidelines 2025", "consumer", "guideline", "ok"),
    ("Digital-Electronic-Online", "digital_lending_regs_2025.pdf", "Digital, Electronic, Online or Non-Traditional Consumer Lending Regulations 2025", "consumer", "regulation", "ok"),
    ("FCCP-Consumer-Protection-Regulations-Exposure", "fccp_consumer_regs_exposure_draft.pdf", "FCCP Consumer Protection Regulations (Exposure Draft)", "consumer", "regulation", "draft_not_in_force"),
    ("Nigeria-Legal-Aid-Act", "legal_aid_act_2011.pdf", "Legal Aid Act 2011", "legal_assistance", "statute", "needs_ocr"),
    ("M6", "marriage_act_cap_m6.pdf", "Marriage Act (Cap M6)", "marriage", "statute", "ok"),
    ("M7", "matrimonial_causes_act_cap_m7.pdf", "Matrimonial Causes Act (Cap M7)", "marriage", "statute", "ok"),
    ("Violence-Against-Persons", "vapp_act_2015.pdf", "Violence Against Persons (Prohibition) Act 2015", "marriage", "statute", "needs_ocr"),
    ("nig120288", "fct_customary_court_act_2007.pdf", "FCT Customary Court Act 2007", "marriage", "statute", "ok"),
    ("C50.pdf", "child_rights_act_2003.pdf", "Child's Right Act 2003", "marriage", "statute", "ok_canonical"),
    ("CUSTOMARY-LAW-MARRIAGE", "customary_marriage_article.pdf", "Customary Law Marriage in Nigeria (article)", "marriage", "article", "secondary_source"),
    ("284-957-1-PB", "contract_customary_islamic_article.pdf", "Principles of Contract under Customary and Islamic Law (article)", "support", "article", "secondary_source"),
    ("crc_copy", "un_crc_convention.pdf", "UN Convention on the Rights of the Child", "support", "treaty", "international_not_nigerian_law"),
]

# (old name starts with, destination folder, reason)
MOVE = [
    ("C50_copy", EXCLUDED, "duplicate of C50 (Child Rights Act)"),
    ("Nigeria - Child Rights Act", EXCLUDED, "duplicate of C50 (OCR errors)"),
    ("global_legal_ai_sources", DOCS, "source list, not a legal text"),
    ("nigerian_legal_research_sources", DOCS, "source list, not a legal text"),
    ("LAWS-OF-THE-FEDERATION-OF-NIGERIA", EXCLUDED, "one-page site cover"),
    ("Revised-treaty", EXCLUDED, "ECOWAS treaty, off-topic"),
]


def find(prefix, files):
    hits = [f for f in files if f.name.startswith(prefix)]
    if prefix == "M6" or prefix == "M7":
        hits = [f for f in files if f.name in (prefix + ".pdf",)]
    if prefix == "JUDGMENTpdf":
        hits = [f for f in files if f.name == "JUDGMENTpdf.pdf"]
    return hits


def main():
    apply = "--apply" in sys.argv
    files = [f for f in sorted(RAW.glob("*.pdf"))]
    used, rows = set(), []
    print("MODE:", "APPLY" if apply else "DRY RUN (nothing will change)")

    for prefix, new, title, area, dtype, status in KEEP:
        hits = [h for h in find(prefix, files) if h not in used]
        if len(hits) != 1:
            print(f"!! {prefix!r}: expected 1 match, found {len(hits)} -> skipped")
            continue
        src = hits[0]
        used.add(src)
        print(f"RENAME  {src.name[:50]:50} -> {new}")
        if apply:
            src.rename(RAW / new)
        rows.append({"doc_id": Path(new).stem, "title": title, "file": new,
                     "problem_area": area, "doc_type": dtype, "status": status,
                     "source_url": "", "date_downloaded": DOWNLOADED,
                     "canonical": "yes" if status != "draft_not_in_force" else "no",
                     "notes": ""})

    for prefix, dest, reason in MOVE:
        hits = [h for h in find(prefix, files) if h not in used]
        for src in hits:
            used.add(src)
            print(f"MOVE    {src.name[:50]:50} -> {dest}/  ({reason})")
            if apply:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest / src.name))

    left = [f.name for f in files if f not in used]
    if left:
        print("\nNot matched (left alone):", *left, sep="\n  ")

    if apply and rows:
        out = DRAFT if REGISTER.exists() else REGISTER
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nRegister written to {out}")
    elif not apply:
        print("\nLooks right? Run again with --apply")


if __name__ == "__main__":
    main()
