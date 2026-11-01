import pytest

from assistant import guidance_modes as gm


def scenarios(q):
    return gm.classify_question(q)["scenarios"]


@pytest.mark.parametrize("question,expected", [
    ("What is bail?", "legal_definition"),
    ("What does section 35 of the Constitution say?", "constitutional_explanation"),
    ("What are my rights when police stop me?", "rights_related"),
    ("How do I report a loan app that harasses me?", "legal_procedure"),
    ("My landlord wants me out tomorrow", "legal_application"),
])
def test_scenario_detected(question, expected):
    assert expected in scenarios(question)


def test_several_scenarios_can_match():
    assert {"legal_procedure", "legal_application"} <= set(scenarios("How long can police hold me?"))


@pytest.mark.parametrize("question,topic", [
    ("I was arrested, what now?", "arrest"),
    ("Can my landlord evict me tomorrow?", "tenant"),
    ("My employer has not paid my salary", "employment"),
    ("A loan app keeps harassing me over a debt", "consumer"),
    ("How do I get a divorce?", "marriage"),
    ("Someone is building on my plot of land", "land"),
    ("I need a free lawyer", "legal_aid"),
])
def test_topic_detected(question, topic):
    assert topic in gm.classify_question(question)["topics"]


def test_land_does_not_match_landlord():
    assert gm.classify_question("Can my landlord raise the rent?")["topics"] == ["tenant"]


def test_problem_areas_for_retrieval():
    areas = gm.classify_question("Can my landlord evict me?")["problem_areas"]
    assert areas == ["tenant", "all_areas"]
    assert gm.classify_question("What is justice?")["problem_areas"] == []   # no topic: search everything


def test_problem_areas_match_the_source_register_values():
    valid = {"arrest", "land", "tenant", "consumer", "marriage", "employment",
             "legal_assistance", "support", "all_areas"}
    for areas in gm.PROBLEM_AREAS.values():
        assert set(areas) <= valid


def test_off_topic_is_out_of_scope():
    assert scenarios("Give me a recipe for jollof") == ["out_of_scope"]
    assert scenarios("Who won the football match?") == ["out_of_scope"]


def test_legal_question_with_off_topic_word_is_kept():
    assert "out_of_scope" not in scenarios("Can I sue the football club over my contract?")


def test_no_legal_content_gives_no_scenario():
    assert scenarios("Hello there") == []


def test_follow_up_keeps_topic_from_history():
    history = [{"role": "user", "content": "My landlord wants me out"}]
    assert gm.classify_question("And what notice is needed?", history)["topics"] == ["tenant"]
    assert gm.classify_question("And what notice is needed?")["topics"] == []   # no history, no topic


def test_select_modes_uses_the_scenarios():
    modes = gm.select_guidance_modes({"scenarios": ["legal_definition", "rights_related"]})
    assert [m["scenario"] for m in modes] == ["legal_definition", "rights_related"]
    assert modes[0]["mode"] == "educational_explanation"


def test_no_scenario_falls_back_to_out_of_scope():
    assert gm.select_guidance_modes({})[0]["scenario"] == "out_of_scope"
    assert gm.select_guidance_modes({"scenarios": ["nonsense"]})[0]["scenario"] == "out_of_scope"


def test_mode_instructions_for_the_prompt():
    text = gm.build_mode_instructions(gm.select_guidance_modes({"scenarios": ["legal_definition"]}))
    assert text.startswith("Guidance for this question:")
    assert "Define the legal concept in simple language." in text
    assert "\n        " not in text                       # indentation cleaned up


def test_out_of_scope_adds_no_instructions_and_prompt_is_capped():
    assert gm.build_mode_instructions(gm.select_guidance_modes({"scenarios": ["out_of_scope"]})) == ""
    many = gm.select_guidance_modes({"scenarios": [
        "legal_definition", "constitutional_explanation", "rights_related", "legal_procedure"]})
    assert gm.build_mode_instructions(many).count("\n- ") == gm.MAX_MODES_IN_PROMPT
