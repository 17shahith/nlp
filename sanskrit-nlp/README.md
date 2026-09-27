# Sanskrit Vakya Nirmata (संस्कृत वाक्य निर्माता)

A rule-based Sanskrit sentence generation system. Given a comma-separated
list of known Sanskrit (Devanagari) or English words, it deterministically
looks up their meaning, classifies them, retrieves their grammar, applies
an explicit set of Sanskrit grammar rules, assigns sentence roles, inflects
each word into the correct stored form, and arranges the result into a
grammatically valid Sanskrit sentence with its English meaning.

**Sentence generation is 100% rule-based.** Groq (an LLM) is never used to
produce or modify the generated sentence or its meaning. Groq is an
optional add-on for two things only: explaining *why* a successful
sentence is correct, and suggesting a vocabulary entry for an unknown
word (which a human must approve before it is ever used). The app works
fully with no `GROQ_API_KEY` set.

## Architecture

```
                     ┌─────────────────────────┐
                     │   frontend/ (static)     │
                     │  index / dictionary /    │
                     │  rules / tests .html+js  │
                     └────────────┬─────────────┘
                                  │ fetch("/api/...")
                     ┌────────────▼─────────────┐
                     │      backend/main.py      │
                     │  FastAPI app + routers    │
                     └────────────┬─────────────┘
        ┌───────────────┬─────────┼─────────┬────────────────┐
        ▼               ▼         ▼         ▼                ▼
   generate.py   dictionary.py rules_api.py tests_api.py  assist.py
        │               │                                     │
        ▼               ▼                                     ▼
  modules/pipeline.py orchestrates:                     modules/groq_helper.py
        │                                                (optional, never touches
        ▼                                                 the generated sentence)
  1 normalizer.py    -> clean/split tokens
  2 vocabulary.py    -> SUB-TASK 1: Sanskrit<->English lookup
  3 classifier.py    -> SUB-TASK 2: word category
  4 grammar_info.py  -> SUB-TASK 3: gender/number/case/person/tense
  5 rules.py         -> SUB-TASK 4: R1-R10 grammar rule engine
  6 role_assigner.py -> SUB-TASK 5a: Subject/Object/Verb/Adjective roles
  7 inflector.py     -> SUB-TASK 5b: pick the correct stored form
  8 sentence_builder -> SUB-TASK 5c: templates -> Sanskrit + IAST + English
        │
        ▼
   db.py (Motor) ──► MongoDB: words / rules / generation_logs
```

## How each sub-task is implemented

| Sub-task | File | What it does |
|---|---|---|
| 1. Word meaning lookup | `modules/vocabulary.py` | Matches a Devanagari token against stored inflected forms (then lemma), or an English token against `english_aliases` / verb conjugations. Returns `None` for anything not in the vocabulary -- it never guesses. |
| 2. Category classification | `modules/classifier.py` | Reads the `category` field already stored on the matched word. |
| 3. Grammar info retrieval | `modules/grammar_info.py` | Reads gender/number/case/vibhakti/person/tense straight off the matched stored form when the user gave an exact Devanagari word; falls back to a "number hint" (singular/plural) from the vocabulary layer when the user gave an English word. |
| 4. Grammar rules | `modules/rules.py` | Ten explicit if/else rules (R1-R10, see below), each returning a `RuleResult`. Hard rules block generation; soft rules (like R7's "usually transitive" case) are warnings only. |
| 5a. Role assignment | `modules/role_assigner.py` | Exactly one Verb; every Pronoun is a Subject; Nouns become Subject/Object by explicit case (if given) or by animacy + input order; every Adjective attaches to its nearest noun. |
| 5b. Inflection | `modules/inflector.py` | Picks the exact stored form for each role (nominative/accusative/agreeing verb form/agreeing adjective form). An explicit Devanagari input is used as-is and never silently "fixed". Missing forms produce a clear error, never a guess. |
| 5c. Templates & output | `modules/sentence_builder.py` | Applies template T1 (Subject+Object+Verb) or T2 (Subject+Verb), transliterates to IAST, and builds the English gloss by template + lookup (pronoun mapping, verb conjugation, "go" + destination phrasing). |

`modules/pipeline.py` runs all of the above in order and returns the exact
step-by-step trace shape used by the frontend and the assignment's example
(`1_meaning` ... `6_output`), logging every run to `generation_logs`.

## Setup

```bash
cd sanskrit-nlp
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
# edit .env: set MONGODB_URI (local mongod or a MongoDB Atlas URI).
# GROQ_API_KEY may be left blank -- the app works fully without it.

cd backend
python -m seed.seed_db          # idempotent: safe to re-run any time
uvicorn main:app --reload       # serves both the API and the frontend

# open http://localhost:8000
```

## Running tests

```bash
cd backend
TESTING=true pytest             # uses a separate "<DB_NAME>_test" database
```

`backend/tests/conftest.py` forces `TESTING=true`, points at a `_test`-suffixed
database, seeds it with the real vocabulary once per session, and drops it
afterwards -- your development database is never touched.

You can also run the same seeded cases through the live server from the
**Tests** page in the UI, or via `POST /api/run-tests`.

## Rules (R1-R10)

| id | rule |
|---|---|
| R1 | Exactly one verb is required. |
| R2 | At least one Subject (noun or pronoun) is required. |
| R3 | The Subject must be nominative (prathama vibhakti). |
| R4 | The Object (if any) must be accusative (dvitiya vibhakti). |
| R5 | The verb's number must match the subject's number. |
| R6 | अहम् needs a 1st-person verb, त्वम् a 2nd-person verb, everything else 3rd-person. |
| R7 | An intransitive verb cannot take an object (hard fail); a transitive verb with no object is a warning, not a failure. |
| R8 | An adjective must match its noun's gender, case, and number. |
| R9 | The same word cannot fill two roles at once. |
| R10 | Every input word must exist in the vocabulary. |

## Templates

- **T1**: `[Adjective?] Subject + [Adjective?] Object + Verb` -- e.g. `रामः मधुरम् फलम् खादति।`
- **T2**: `[Adjective?] Subject + Verb` (no object) -- e.g. `बालकः धावति।`

## Known limitations

- Present tense (लट् lakara) only -- no past, future, or other lakaras.
- A deliberately small, fixed vocabulary (~38 lemmas seeded); unknown words fail rule R10 rather than being guessed.
- No sandhi (word-junction sound changes) between words in the generated sentence.
- No full Sanskrit morphology/declension engine -- only the specific stored forms in the `words` collection are ever produced; a form not seeded for a lemma (e.g. an oblique case) returns a clear "not available" error instead of being derived on the fly.
- Adjective agreement is only implemented for the nominative/accusative singular forms seeded per gender.
- Role assignment's "two animate nouns -> first is Subject" heuristic is a simplification; real Sanskrit relies on case marking, not word order, which is why an explicit Devanagari case always overrides it.
