"""Reviewed plain-English answers for a few high-stakes, frequently asked questions.

Written from the text of the Matrimonial Causes Act (Cap M7), sections 15, 16 and 39.
DRAFT: have a lawyer or your supervisor check the wording before presenting it as verified.
"""
import difflib
import re

DISCLAIMER = "This is general legal information, not legal advice. Please consult a qualified lawyer."

FACTS = """1. The other spouse has wilfully and persistently refused to consummate the marriage (to have sexual relations after the wedding).
2. Since the marriage, the other spouse has committed adultery (had sex with someone else) and you find it intolerable to live with them.
3. Since the marriage, the other spouse has behaved in a way that you cannot reasonably be expected to live with them.
4. The other spouse has deserted you (left you) for a continuous period of at least one year just before the petition.
5. You have lived apart for a continuous period of at least two years just before the petition, and the other spouse does not object to the divorce being granted.
6. You have lived apart for a continuous period of at least three years just before the petition. The other spouse's agreement is not needed.
7. The other spouse has, for at least one year, failed to obey a court order to restore conjugal rights (to resume living together as husband and wife).
8. The other spouse has been absent so long, and in such circumstances, that there are reasonable grounds to believe he or she is dead."""

DIVORCE = f"""**Grounds for divorce (dissolution of marriage)**

**Short answer:** The ground for divorce is that the marriage has broken down irretrievably (beyond repair). The court accepts this only if the person asking for the divorce proves at least one of eight facts.

**What the law says:** [Matrimonial Causes Act (Cap M7), section 15] The facts are:

{FACTS}

Spouses count as living apart unless they live with each other in the same household.

**What you can do:** A lawyer or the Legal Aid Council can help you work out which fact fits your situation and prepare the petition.

{DISCLAIMER}"""

SEPARATION = f"""**Grounds for judicial separation**

**Short answer:** Judicial separation is a court order that spouses no longer have to live together, while the marriage continues. A petition for it can rely on the same facts that can support a divorce.

**What the law says:** [Matrimonial Causes Act (Cap M7), section 39] says a petition for judicial separation may be based on one or more of the facts and matters in sections 15(2) and 16(1). [Matrimonial Causes Act (Cap M7), section 15] lists the facts:

{FACTS}

Section 16(1) adds more detail about what counts as the behaviour in fact 3.

**What you can do:** A lawyer or the Legal Aid Council can help you decide whether judicial separation or divorce suits your situation.

{DISCLAIMER}"""

# (groups of words: at least one word from every group must be in the question, answer)
CURATED = [
    ([{"grounds", "ground", "reasons"}, {"separation", "separated"}], SEPARATION),
    ([{"grounds", "ground", "reasons"}, {"divorce", "dissolution", "divorcing"}], DIVORCE),
]


def lookup_curated(question):
    """Return a reviewed answer if the question matches, else None. Tolerates small typos."""
    words = re.findall(r"[a-z]+", question.lower())
    has = lambda w: w in words or bool(difflib.get_close_matches(w, words, n=1, cutoff=0.8))
    for groups, answer in CURATED:
        if all(any(has(w) for w in group) for group in groups):
            return answer
    return None
