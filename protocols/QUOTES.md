# QUOTES — Reference Questionnaire Ingest & Apply

Run this protocol when adding a new reference questionnaire (from Cecilia, Syrak, or another candidate) and when applying quotes from the corpus to Daria's questionnaire files.

## Part 1: Ingest a New Reference Questionnaire

### Inputs

- The source document (Google Doc ID, PDF, or text)
- The candidate's name, office, district, cycle, and the org that issued the questionnaire

### Steps

1. **Read the full source document.** Use the Google Drive MCP tool (`read_file_content`) for Google Docs, or read the PDF/text directly.

2. **Register in sources.json.** Add an entry under `reference_corpus.{candidate_slug}`:
   ```json
   {
     "description": "Org Name Questionnaire",
     "drive_file_id": "...",
     "type": "google_doc|pdf"
   }
   ```
   If the candidate does not yet have a `reference_corpus` entry, create one with `name`, `office`, `cycle`, and `documents` array.

3. **Extract topic-relevant quotes.** For each answer in the source questionnaire:
   - Match it to one of the controlled topics in CONVENTIONS.md.
   - Extract verbatim text — do not paraphrase or compress. Short passages (1–4 sentences) are better than full answers.
   - Write a one-line `relevance` note explaining why this quote matters for Daria's corresponding question.

4. **Fact-check every quote for staleness.** For each extracted quote, check whether any program, policy, ordinance, or fact it references has changed since the source questionnaire was written. Known stale items as of July 2026:
   - **Specialized Care Unit**: transferred to Alameda County; no longer a Berkeley city program
   - **Mobile Crisis Team**: closed by Berkeley
   - **Berkeley Wellness Center**: closed
   - **Prop 33 (rent control)**: failed November 2024 — references to it as a future ballot measure are stale; references as historical fact are current
   - **TOPA**: council voted against it October 2024; referred to City Manager February 2026. Cecilia Lunaparra is re-introducing amended language. Support for TOPA is current; claims that it exists or is enacted are stale.
   - **BerkDOT**: status unresolved as of July 2026

   Set `status` to `stale` and write a specific `stale_note` for any affected quote. See CONVENTIONS.md § Quote status definitions.

5. **Apply the framing rule.** Review every extracted quote against the framing rule in CONVENTIONS.md:
   - Biographical claims (personal history, family background, identity) → do NOT use as quotes for Daria's questions
   - Endorsement lists → do NOT use
   - Policy positions and framing → safe to use as reference material
   - Organizational memberships → do NOT use

## Part 2: Apply Quotes to Questionnaire Files

### When to run

After ingesting new reference questionnaires, or when a new org questionnaire is added via INGEST.md.

### Steps

1. **List all questions across all org files** with their topics and statuses.

2. **Match quotes to questions by topic.** For each question:
   - Check all reference questionnaires for answers on the same controlled topic.
   - Only add a quote if there is a **genuine analogue** — the reference candidate addressed the same policy area with enough specificity to be useful framing.
   - Leave the `quotes` field absent (not empty array) where no good match exists.

3. **Prioritize blank and thin questions.** These benefit most from framing references. Done questions may also get quotes if the match is strong, but do not over-populate.

4. **Build the quotes array.** Each entry:
   ```json
   {
     "source": "cecilia|syrak|campaign",
     "attribution": "Full Name — Org Questionnaire, Year",
     "text": "verbatim quote",
     "relevance": "one-line explanation",
     "status": "current|stale|unverified",
     "stale_note": "required if stale"
   }
   ```

5. **Audit existing suggested copy for borrowed biographical claims.** Grep suggested copy for names, personal details, or experiences that belong to the reference candidate, not Daria. Remove any that violate the framing rule.

6. **Validate JSON.** Run `python3 -c "import json; json.load(open('questionnaires/data/{slug}.json'))"` for every modified file.

## Part 3: Ongoing Staleness Checks

When facts change (a program closes, a policy fails at the ballot), existing quotes may go stale. This is handled by `protocols/REFRESH.md` Mode C, which scans all quotes arrays across all org files and updates `status` / `stale_note` as needed.

Keep the **known stale items** list in Part 1 Step 4 up to date whenever a new staleness is discovered during a refresh cycle.

## Adding New Reference Candidates

The `source` field in quotes objects uses a slug for the reference candidate (e.g., `"cecilia"`, `"syrak"`, `"campaign"`). When adding a new reference candidate:

1. Pick a lowercase slug (first name or last name, no spaces).
2. Add a `reference_corpus.{slug}` entry in `sources.json`.
3. Update CONVENTIONS.md § Quotes schema to add the new slug to the `source` enum comment.
4. Follow Part 1 for each of the new candidate's questionnaires.
5. Follow Part 2 to apply quotes across all existing org files.

## Rules

- Quotes are verbatim. Do not paraphrase, compress, or edit the source text.
- Do not add empty quotes arrays. Missing = never checked; empty = checked, found nothing. The distinction is load-bearing.
- No biographical borrowing. The framing rule in CONVENTIONS.md is absolute.
- No gendered or second-person pronouns in `relevance` fields. Use "the candidate" when referring to Daria.
- Stale quotes stay in the system with warnings — they show what the framing landscape looked like and prevent the candidate from unknowingly citing outdated facts.
- When multiple quotes match a single question, prefer the most specific and concise one. Two quotes maximum per question unless the topic genuinely requires more.
- Export intentionally excludes quotes — they are framing references for the campaign team, not text to submit.
