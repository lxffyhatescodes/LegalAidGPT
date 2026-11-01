from assistant import citation_validator as cv
from helpers import CONSTITUTION, POLICE_ACT, TENANCY, make_chunk

CHUNKS = [CONSTITUTION, POLICE_ACT]


def test_valid_citation():
    v = cv.validate_citations("Taken to court [Constitution of Nigeria 1999, section 35].", CHUNKS)
    assert v["has_citations"] and v["is_valid"] and v["citation_count"] == 1
    assert v["invalid_citations"] == [] and v["used_chunks"] == [0]


def test_lenient_formats_are_accepted():
    for ref in ("[Constitution of Nigeria 1999, s. 35]", "[Constitution 1999, Section 35(1)]",
                "[constitution of nigeria 1999, sec 35]"):
        assert cv.validate_citations(f"Text {ref}.", CHUNKS)["is_valid"], ref


def test_unknown_source_is_invalid():
    v = cv.validate_citations("See [Tax Act 2020, section 5].", CHUNKS)
    assert v["invalid_citations"] == ["[Tax Act 2020, section 5]"] and not v["is_valid"]


def test_wrong_section_is_invalid():
    v = cv.validate_citations("See [Constitution of Nigeria 1999, section 99].", CHUNKS)
    assert v["invalid_citations"] and v["used_chunks"] == []


def test_mixed_valid_and_invalid():
    v = cv.validate_citations(
        "A [Police Act 2020, section 66] and B [Fake Act, section 1].", CHUNKS)
    assert len(v["valid_citations"]) == 1 and len(v["invalid_citations"]) == 1 and not v["is_valid"]


def test_no_citation():
    v = cv.validate_citations("A person must go to court.", CHUNKS)
    assert not v["has_citations"] and not v["is_valid"]


def test_other_brackets_are_not_citations():
    v = cv.validate_citations("See [1] and [Note, see section 5] and [a link](http://x.com).", CHUNKS)
    assert not v["has_citations"]


def test_source_names_with_commas():
    chunk = make_chunk("Judgment text.", "Esezobor v Emowele, HCU/33/2018 (Edo High Court)", "12")
    v = cv.validate_citations(
        "See [Esezobor v Emowele, HCU/33/2018 (Edo High Court), section 12].", [chunk])
    assert v["is_valid"]


def test_remove_invalid_citations():
    v = cv.validate_citations("A [Fake Act, section 1] B [Police Act 2020, section 66]", CHUNKS)
    cleaned = cv.remove_invalid_citations("A [Fake Act, section 1] B [Police Act 2020, section 66]", v)
    assert "[UNVERIFIED CITATION]" in cleaned and "[Police Act 2020, section 66]" in cleaned
    assert "Fake Act" not in cleaned


def test_citations_for_ui_has_the_keys_the_ui_needs():
    v = cv.validate_citations("[Constitution of Nigeria 1999, section 35]", CHUNKS)
    items = cv.citations_for_ui(v, CHUNKS)
    assert set(items[0]) == {"chunk_id", "doc_title", "section", "excerpt"}
    assert items[0]["doc_title"] == "Constitution of Nigeria 1999" and items[0]["section"] == "35"


def test_figures_must_be_in_the_sources():
    assert cv.find_unsupported_figures("Notice of 48 hours is needed.", [TENANCY]) == []   # source says forty-eight
    assert cv.find_unsupported_figures("Notice of 72 hours is needed.", [TENANCY]) == ["72 hours"]


def test_figures_from_the_question_are_allowed():
    assert cv.find_unsupported_figures("You were held for 2 days.", CHUNKS,
                                       question="I was held for 2 days") == []


def test_money_and_percent():
    assert cv.find_unsupported_figures("The fine is N5,000 or 10%.", CHUNKS) == ["N5,000", "10%"]
    chunk = make_chunk("A fine of N5,000 applies.", "Police Act 2020", "9")
    assert cv.find_unsupported_figures("The fine is N5,000.", [chunk]) == []


def test_numbers_inside_citations_and_years_are_ignored():
    assert cv.find_unsupported_figures(
        "See [Constitution of Nigeria 1999, section 35] and the Act of 2015.", CHUNKS) == []
