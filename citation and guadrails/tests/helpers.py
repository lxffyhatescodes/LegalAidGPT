def make_chunk(text, source, section, similarity=0.8):
    return {"text": text, "metadata": {"source": source, "section": section},
            "similarity": similarity}


CONSTITUTION = make_chunk(
    "35. (1) Test passage: a person who is arrested or detained shall be brought before a "
    "court within a reasonable time.", "Constitution of Nigeria 1999", "35")
POLICE_ACT = make_chunk(
    "Test passage: a police officer shall inform an arrested person of the reason for arrest.",
    "Police Act 2020", "66")
TENANCY = make_chunk(
    "Test passage: a landlord must give forty-eight hours notice before entering the premises.",
    "Nigeria Tenant Rights Legal Document Starter Pack", "4")
