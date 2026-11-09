"""Plain-English glossary of common legal terms (instant answers, no model needed).

DRAFT: written for the project from general legal knowledge. Have a lawyer or your
supervisor review the wording before you present it as verified.
"""
import re

DISCLAIMER = "This is general legal information, not legal advice. Please consult a qualified lawyer."
GLOSSARY_TITLE = "Legal-AI plain-English glossary"


def _e(name, meaning, example="", aliases=(), source=None):
    return {"name": name, "meaning": meaning, "example": example, "aliases": tuple(aliases), "source": source}


ENTRIES = [
    # Arrest, police and criminal cases
    _e("bail", "Bail means being allowed to go home after arrest while you wait for your case, on condition that you come back to the police or the court when required. You may be asked for a promise, money or a surety.",
       "A person arrested for a minor offence may be released on bail and told to return on a set date.", ("bail bond",)),
    _e("surety", "A surety is a person who promises the court or police that an accused person will come back when required. If the accused does not return, the surety may have to pay money.",
       "A relative stands as surety so a suspect can be released on bail.", ("sureties",)),
    _e("recognizance", "A recognizance is a written promise made to a court or police officer, for example to appear at a set time and place. It can be backed by a sum of money that must be paid if the promise is broken, with or without sureties.",
       "The suspect signs a recognizance to report to the police station on Monday.", ("recognisance",)),
    _e("remand", "Remand means keeping an accused person in custody, for example in a correctional centre, while they wait for their trial or the next step in the case.",
       "", ("remanded", "remand in custody")),
    _e("arraignment", "Arraignment is the first formal step in a criminal trial: the charge is read to the accused in court and they are asked whether they plead guilty or not guilty.",
       "", ("arraigned",)),
    _e("charge", "A charge is the formal accusation that someone committed a specific offence. It states what the person is said to have done.",
       "", ("charges", "criminal charge")),
    _e("suspect", "A suspect is a person the police believe may have committed an offence. Being a suspect does not mean the person is guilty.",
       "", ("suspects",)),
    _e("warrant of arrest", "A warrant of arrest is a written order from a court allowing the police to arrest a named person.",
       "", ("arrest warrant", "warrant")),
    _e("summons", "A summons is a court document that orders a person to come to court at a stated time, or tells them that a case has been started against them.",
       "", ("summonses",)),
    _e("capital offence", "A capital offence is a very serious crime for which the law allows the death penalty.",
       "", ("capital offense", "capital offences")),
    _e("reasonable time", "Under section 35 of the Constitution, \"a reasonable time\" for bringing an arrested person before a court means one day where a court is within forty kilometres, and in any other case two days or such longer period as the court considers reasonable. This applies to people arrested on suspicion of an offence under section 35(1)(c).",
       "", ("a reasonable time",), source=("Constitution of the Federal Republic of Nigeria 1999", "35(5)")),
    # Courts and cases
    _e("plaintiff", "A plaintiff, also called a claimant in some courts, is the person who starts a civil case by asking the court for a remedy.",
       "", ("claimant",)),
    _e("defendant", "A defendant is the person or organisation a case is brought against. In a criminal case it is the accused person.",
       "", ("defendants", "accused")),
    _e("judgment", "A judgment is the court's final decision in a case, together with its reasons.",
       "", ("judgement", "judgments")),
    _e("injunction", "An injunction is a court order telling a person to do something or to stop doing something.",
       "", ("injunctions",)),
    _e("affidavit", "An affidavit is a written statement of facts that the person swears is true, usually before an official who can take oaths.",
       "", ("affidavits",)),
    _e("adjournment", "An adjournment is the postponement of a court hearing to another date.",
       "", ("adjourned", "adjourn")),
    _e("jurisdiction", "Jurisdiction is the power of a court to hear and decide a particular case.",
       "", ()),
    _e("appeal", "An appeal is a request to a higher court to review and change a lower court's decision.",
       "", ("appeals",)),
    _e("evidence", "Evidence is the documents, objects or statements shown to a court to prove or disprove the facts of a case.",
       "", ()),
    # Family law
    _e("dissolution of marriage", "Dissolution of marriage is the legal term for divorce: a court order that ends a marriage.",
       "", ("divorce",)),
    _e("decree nisi", "A decree nisi is a court's first, provisional order that a marriage should end. It becomes final only later, as a decree absolute, unless something stops it.",
       "", ()),
    _e("decree absolute", "A decree absolute is the final court order that ends a marriage.",
       "", ()),
    _e("judicial separation", "A judicial separation is a court order that spouses no longer have to live together. The marriage itself does not end.",
       "", ()),
    _e("maintenance", "Maintenance is regular money paid for the support of a spouse or children, usually under a court order or an agreement.",
       "", ()),
    _e("ante-nuptial settlement", "An ante-nuptial settlement is an arrangement about property made before a marriage.",
       "", ("antenuptial settlement", "ante nuptial settlement", "ante-nuptial")),
    _e("post-nuptial settlement", "A post-nuptial settlement is an arrangement about property made after a marriage has taken place.",
       "", ("postnuptial settlement", "post nuptial settlement", "post-nuptial")),
    _e("intestate", "To die intestate means to die without a valid will. The law then decides who receives the person's property.",
       "", ("intestacy",)),
    # Housing
    _e("tenancy", "A tenancy is an arrangement in which a person, the tenant, pays rent to live in or use property owned by someone else, the landlord.",
       "", ("tenancies",)),
    _e("notice to quit", "A notice to quit is a written notice from a landlord telling a tenant to leave the property by a stated date.",
       "", ("quit notice",)),
    # Work
    _e("wages", "Wages are the money an employer pays a worker for work done.",
       "", ("wage",)),
    _e("advance of wages", "An advance of wages is money an employer pays a worker before it is due, which is later taken back out of the worker's wages.",
       "", ("wage advance", "advance")),
    _e("contract of employment", "A contract of employment is an agreement between an employer and a worker about the work, pay and conditions.",
       "", ("employment contract",)),
    # Getting help
    _e("legal practitioner", "A legal practitioner is a lawyer who is qualified and allowed to practise law in Nigeria.",
       "", ("lawyer", "legal practitioners")),
    _e("legal aid", "Legal aid is free or low-cost legal help for people who cannot afford a lawyer. In Nigeria, the Legal Aid Council provides it.",
       "", ()),
    _e("pro bono", "Pro bono work is legal work that a lawyer does for free for people who cannot pay.",
       "", ()),
]

INDEX = {}
for _entry in ENTRIES:
    INDEX[_entry["name"]] = _entry
    for _alias in _entry["aliases"]:
        INDEX[_alias] = _entry

# Only whole questions that ask what a term means, such as "What does bail mean?".
PATTERN = re.compile(
    r"^(?:what is the meaning of|what is the definition of|meaning of|definition of"
    r"|what(?:'s| is| does| do you mean by)|define|explain|tell me about)"
    r"\s+(?:a |an |the )?(?P<term>.+?)"
    r"(?:\s+(?:mean|means|in (?:simple|plain)(?: english| terms| words| language)?|to me|please))*\s*$"
)


def lookup_term(question):
    """Return the glossary entry if the question asks what a listed term means, else None."""
    q = re.sub(r"[^a-z0-9'\- ]+", " ", question.lower().replace("\u2019", "'"))
    q = re.sub(r"\s+", " ", q).strip()
    m = PATTERN.match(q)
    return INDEX.get(m.group("term").strip()) if m else None


def format_answer(entry):
    parts = [f"**{entry['name'].capitalize()}**", entry["meaning"]]
    if entry["example"]:
        parts.append(f"*Example:* {entry['example']}")
    parts.append(DISCLAIMER)
    return "\n\n".join(parts)


def citation(entry):
    """The source card shown under the answer in the app."""
    doc, section = entry["source"] if entry["source"] else (GLOSSARY_TITLE, entry["name"])
    return {"chunk_id": "glossary-" + entry["name"].replace(" ", "-"), "doc_title": doc,
            "section": section, "excerpt": entry["meaning"]}
