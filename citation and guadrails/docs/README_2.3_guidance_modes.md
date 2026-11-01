# 2.3 Scenario-based guidance modes

**File:** `assistant/guidance_modes.py`   **Tests:** `tests/test_guidance_modes.py`

## What it does
1. `classify_question(question)` reads the question and returns:
   - `scenarios`: what kind of question it is (definition, constitutional, rights, procedure, situation, or out_of_scope)
   - `topics`: which legal area it is about (arrest, tenant, land, consumer, marriage, employment, legal_aid)
   - `problem_areas`: the document groups to search (matches the `problem_area` column in `source_register.csv`)
2. `select_guidance_modes(classification)` picks the matching entries from `GUIDANCE_MODES`.
3. `build_mode_instructions(modes)` turns them into a short text that is added to the prompt.

## Change it
- Edit the wording in `GUIDANCE_MODES` to change how each kind of question is answered.
- Add words to `TOPIC_KEYWORDS` / `SCENARIO_PATTERNS` when a question is classified wrongly. A word ending in `*` matches any ending (`evict*` = evicted, eviction).

## Run the tests
    python -m pytest tests/test_guidance_modes.py
