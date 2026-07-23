# INGEST — New Questionnaire

Run this protocol in a Claude Code session when adding a new organization's questionnaire to the system.

## Inputs

- The PDF or text of the organization's blank questionnaire
- The candidate's name, office, and cycle
- Any existing research on the organization

## Steps

1. **Create the JSON file.** Copy `questionnaires/data/nuhw.json` as a template. Save as `questionnaires/data/{slug}.json`.

2. **Fill the header fields.**
   - `slug`: lowercase, no spaces (e.g., `seiuusww`)
   - `org`: full legal name
   - `cycle`: election year (e.g., `"2026"`)
   - `candidate`: name + office (e.g., `"Daria Wrubel — Berkeley City Council D1"`)
   - `generated`: today's date (ISO)
   - `last_factcheck`: today's date (ISO)
   - `org_research`: 2–4 sentence summary of the org's priorities and endorsement criteria

3. **Fill `contact_fields`.** One object per field: `{ "k": "slug", "label": "Display Label", "v": "value" }`.

4. **Port every question VERBATIM.** For each question in the source questionnaire, create an object in the `questions` array. The `question` field must be a character-for-character copy of the source text, including the org's own typos, capitalization, and punctuation. Do not rephrase, merge, split, or "clean up" question text.
   ```
   {
     "id": "{slug}_q{n}",
     "section": "Section N: Title",
     "topic": "<one of the controlled topics>",
     "status": "blank",
     "question": "verbatim question text — character-for-character from source",
     "analysis": "",
     "references": [],
     "levers": [],
     "sources": [],
     "suggested": [],
     "verification": []
   }
   ```

5. **Assign topics** from the controlled list:
   `why_running`, `background_bio`, `endorsement_ask`, `labor_solidarity`, `labor_law`, `healthcare_standards`, `disease_protection`, `behavioral_health`, `single_payer`, `voting_rights`, `dei_trans_care`, `cultural_competence`, `immigration`, `ice_cooperation`, `affordable_housing`, `rent_control`, `homelessness`, `campaign_plan`, `endorsements`

6. **PREMISE VERIFICATION (mandatory, before any levers or copy).** Every question embeds assumptions about the jurisdiction — that it has a program, a mechanism, an authority, a contract, a department. For each question:
   - Extract every jurisdiction-specific assumption the question makes
   - Verify each assumption against a **primary source**: the city's own site, ordinance text, council agenda, adopted budget, MOU, or benefits guide. Secondary sources and general knowledge are NOT sufficient for jurisdiction-specific claims.
   - Record the result in the `verification` array:
     ```
     { "claim": "what was checked", "result": "confirmed|refuted|unresolved", "source": "primary source name", "date": "ISO date", "note": "" }
     ```
   - If a premise is **refuted**, that is the most valuable finding on the page. The answer becomes "our jurisdiction does not work that way, here is what we actually have." Update the analysis and levers to reflect reality.
   - If a premise is **unresolved** and load-bearing, set status to `"blocked"`. See step 8.
   - Flag any source older than two years for re-confirmation.

7. **Generate analysis, levers, and suggested copy.** For each question:
   - `analysis`: research-backed context on the topic as it relates to the candidate's platform and the org's priorities
   - `levers`: array of objects with tiered tags. See CONVENTIONS.md § Lever tiering for tier definitions.
   - `sources`: array of `{ "label": "...", "url": "..." }` — verified, live links only. For jurisdiction-specific mechanics, require a primary source (city site, ordinance, budget, MOU, benefits guide).
   - `suggested`: array of `{ "note": "", "text": "draft copy" }` — written per the copy rules in CONVENTIONS.md § Copy rules, with `[bracketed notes]` where firsthand detail is needed. Leave `note` as an empty string (the renderer requires the field but subtitles are not used).
   - Set `status` per step 8.

8. **Set status.** See CONVENTIONS.md § Status definitions for the full list. Key rule: `blocked` questions get NO suggested copy.

9. **Register the slug** in the gallery. Add the slug string to the `KNOWN_ORGS` array in `questionnaires/index.html`.

10. **Add to due dates and sync.** Add a `null` entry for the slug in `questionnaires/data/due_dates.json` and add the org's name(s) to the `ORG_MAP` in `.github/workflows/sync-due-dates.yml`.

11. **Validate the JSON.** Run `python3 -c "import json; json.load(open('questionnaires/data/{slug}.json'))"` to confirm valid JSON.

12. **Seed a status row** (optional). Insert into `questionnaire_status` via Supabase:
    ```sql
    insert into questionnaire_status (org_slug, display_name, priority, category, timing)
    values ('{slug}', '{Org Name}', 'high', 'labor', '2026-08-15');
    ```

## Copy Rules

See CONVENTIONS.md § Copy rules. The canonical definitions live there to prevent drift.

## Output

- `questionnaires/data/{slug}.json` — committed to git
- `questionnaires/index.html` — updated KNOWN_ORGS array
- `questionnaires/data/due_dates.json` — updated with null entry
- `.github/workflows/sync-due-dates.yml` — updated ORG_MAP
- `questionnaire_status` row in Supabase (optional)

## Rules

See CONVENTIONS.md § Rules for the full list. Key rules repeated here for emphasis:
- Port questions verbatim — character-for-character from source, including the org's own typos
- Every authority lever must have a verification entry confirming the jurisdiction has that power
- Blocked questions get no suggested copy — a "confirm this" note on finished-looking copy is the failure mode
