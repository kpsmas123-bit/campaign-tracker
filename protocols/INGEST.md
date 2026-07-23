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

4. **Port every question.** For each question in the source questionnaire, create an object in the `questions` array:
   ```
   {
     "id": "{slug}_q{n}",
     "section": "Section N: Title",
     "topic": "<one of the controlled topics>",
     "status": "blank",
     "question": "verbatim question text",
     "analysis": "",
     "references": [],
     "levers": [],
     "sources": [],
     "suggested": []
   }
   ```

5. **Assign topics** from the controlled list:
   `why_running`, `background_bio`, `endorsement_ask`, `labor_solidarity`, `labor_law`, `healthcare_standards`, `disease_protection`, `behavioral_health`, `single_payer`, `voting_rights`, `dei_trans_care`, `cultural_competence`, `immigration`, `ice_cooperation`, `affordable_housing`, `rent_control`, `homelessness`, `campaign_plan`, `endorsements`

6. **Generate analysis and suggested copy.** For each question:
   - `analysis`: research-backed context on the topic as it relates to the candidate's platform and the org's priorities
   - `levers`: array of `{ "tier": "authority"|"advocacy", "text": "..." }` — what a councilmember can actually do
   - `sources`: array of `{ "label": "...", "url": "..." }` — verified, live links only
   - `suggested`: array of `{ "note": "short label", "text": "draft copy" }` — in the candidate's voice, with `[bracketed notes]` where firsthand detail is needed
   - Set `status` to `"done"` when analysis + suggested are complete, `"thin"` if partial, `"verify"` if sources need checking

7. **Register the slug** in the gallery. Add the slug string to the `KNOWN_ORGS` array in `questionnaires/index.html`.

8. **Validate the JSON.** Run `python3 -c "import json; json.load(open('questionnaires/data/{slug}.json'))"` to confirm valid JSON.

9. **Seed a status row** (optional). Insert into `questionnaire_status` via Supabase:
   ```sql
   insert into questionnaire_status (org_slug, display_name, priority, category, timing)
   values ('{slug}', '{Org Name}', 'high', 'labor', '2026-08-15');
   ```

## Output

- `questionnaires/data/{slug}.json` — committed to git
- `questionnaires/index.html` — updated KNOWN_ORGS array
- `questionnaire_status` row in Supabase (optional)

## Rules

- Do not include answers in the JSON — those go to Supabase via the editor
- Do not reference AI, Claude, or models in any generated text — use neutral labels (analysis, research, strategy)
- Port questions verbatim — do not rephrase or merge
- Every source URL must be verified as live before marking status as "done"
