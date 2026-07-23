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
   `why_running`, `background_bio`, `endorsement_ask`, `labor_solidarity`, `labor_law`, `healthcare_standards`, `disease_protection`, `behavioral_health`, `single_payer`, `voting_rights`, `dei_trans_care`, `cultural_competence`, `immigration`, `ice_cooperation`, `affordable_housing`, `rent_control`, `housing_affordability`, `anti_displacement`, `tenant_protections`, `rent_stabilization`, `homelessness`, `campaign_plan`, `endorsements`

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
   - `levers`: array of objects with tiered tags:
     - `"authority"`: council has direct power (zoning, budget, ordinance, appointment). NEVER tag something authority on an assumed mechanism — each authority lever must have a verification entry confirming this jurisdiction actually has that power.
     - `"advocacy"`: council can only pass resolutions, lobby, or use bully pulpit
     - `"unverified"`: mechanism has not been confirmed for this jurisdiction. Renders in a warning style. Never appears in exported drafts.
   - `sources`: array of `{ "label": "...", "url": "..." }` — verified, live links only. For jurisdiction-specific mechanics, require a primary source (city site, ordinance, budget, MOU, benefits guide).
   - `suggested`: array of `{ "note": "short label", "text": "draft copy" }` — written in first person ("I support…", "I would…"), with `[bracketed notes]` where firsthand detail is needed. See **Copy Rules** below.
   - Set `status` per the status rules in step 8.

8. **Set status.** Each question gets exactly one status:
   - `"done"`: analysis, levers, and suggested copy are complete. All verification entries are `confirmed` or `refuted` (and the content reflects reality). All source URLs are live.
   - `"thin"`: analysis is partial or sources are incomplete, but no unresolved blocking facts.
   - `"verify"`: sources need link-checking or content re-verification.
   - `"blocked"`: a load-bearing fact cannot be resolved from a primary source. The question has a verification entry with `result: "unresolved"` and a note saying what specifically needs confirming and where to look. **DO NOT generate suggested copy for blocked questions.** Blocked questions render visibly in the UI and are excluded from export until resolved.
   - `"blank"`: no research has been done.

9. **Register the slug** in the gallery. Add the slug string to the `KNOWN_ORGS` array in `questionnaires/index.html`.

10. **Add to due dates and sync.** Add a `null` entry for the slug in `questionnaires/data/due_dates.json` and add the org's name(s) to the `ORG_MAP` in `.github/workflows/sync-due-dates.yml`.

11. **Validate the JSON.** Run `python3 -c "import json; json.load(open('questionnaires/data/{slug}.json'))"` to confirm valid JSON.

12. **Seed a status row** (optional). Insert into `questionnaire_status` via Supabase:
    ```sql
    insert into questionnaire_status (org_slug, display_name, priority, category, timing)
    values ('{slug}', '{Org Name}', 'high', 'labor', '2026-08-15');
    ```

## Copy Rules

- **First person.** Suggested copy is draft text the candidate submits. Write in first person: "I support…", "I would…", "my Council seat…". Use "the candidate" or "Daria" only in analysis, levers, and other non-copy fields.
- **No hedged facts.** Suggested copy may NEVER contain an unresolved factual disjunction about the jurisdiction. Forbidden patterns: "either X or Y," "whether we use X or Y," "in most cities," and any construction that papers over something checkable. A verifiable fact is resolved, or it is omitted and flagged. It is never hedged.
- **No AI/Claude/model references.** Use neutral labels (analysis, research, strategy).
- **Asymmetric risk.** A blank answer costs nothing. A confidently wrong specific costs the endorsement and the credibility. When in doubt, leave it out and flag it.

## Output

- `questionnaires/data/{slug}.json` — committed to git
- `questionnaires/index.html` — updated KNOWN_ORGS array
- `questionnaires/data/due_dates.json` — updated with null entry
- `.github/workflows/sync-due-dates.yml` — updated ORG_MAP
- `questionnaire_status` row in Supabase (optional)

## Rules

- Do not include answers in the JSON — those go to Supabase via the editor
- Port questions verbatim — character-for-character from source, including the org's own typos
- Every source URL must be verified as live before marking status as "done"
- Every authority lever must have a verification entry confirming the jurisdiction has that power
- Blocked questions get no suggested copy — a "confirm this" note on finished-looking copy is the failure mode
- Source date must be recorded; flag anything older than two years
