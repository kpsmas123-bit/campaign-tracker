# CONVENTIONS — Questionnaire System

## Supabase

- **Project URL**: `https://qhrtqtnrduambvchjxqw.supabase.co`
- **Publishable key**: `sb_publishable_UAG7Ru6PRdNnOLCbchpQVg_8vE0jG5N`
- **Config location**: hardcoded in `index.html`, `questionnaires/questionnaire.html`, and `questionnaires/index.html`
- **Auth user**: `questionnaire@dariaforberkeley.com` (UID `1c6344d4-6cd5-458a-846f-cfd619d51f4a`)

### Shared project exposure

Campaign-tracker and DESK share one Supabase project. The existing tables (`tasks`, `team_members`, `campaign_settings`) have permissive `using (true)` RLS — any request with the anon key can read/write them. The questionnaire tables (`questionnaire_answers`, `questionnaire_status`) are the exception: their RLS is locked to the shared auth user's UID. Do not change the existing tables' RLS in this build.

## Design tokens

All pages must use these tokens from `index.html`:

| Token | Value |
|---|---|
| `--ground` | `#F9F9F6` (warm off-white) |
| `--surface` | `#FFFFFF` |
| `--text` | `#2A2A2E` |
| `--text-secondary` | `#7C7C82` |
| `--text-tertiary` | `#A8A8AC` |
| `--border` | `#E6E6E2` |
| `--accent` | `#4A6FA5` |
| `--priority-high` | `#C45240` + `12` opacity bg |
| `--priority-medium` | `#C89B2A` + `12` opacity bg |
| `--priority-low` | `#6B956B` + `12` opacity bg |

### Typography

- **Titles**: `Georgia, 'Times New Roman', serif` — 20–22px, normal weight
- **Body**: `system-ui, -apple-system, sans-serif` — 14px
- **Labels/mono**: `IBM Plex Mono` — 10–11px, uppercase, letter-spacing 0.06em
- **No shadows** anywhere. Border-radius 2–3px max.

### Component patterns

- **Priority pills**: colored dot + label, wash-bg at 7% opacity (`#C4524012`)
- **Filter buttons**: flat text, underline on active, uppercase 11px mono
- **Checkboxes**: 16x16, 2px radius, accent border on hover, green fill when checked
- **Rows**: grid layout, 1px border-bottom, hover background `--hover`

## File structure

```
campaign-tracker/
  index.html                    # campaign task tracker (DO NOT MODIFY)
  setup.sql                     # original schema (DO NOT MODIFY)
  questionnaire_setup.sql       # questionnaire tables migration
  questionnaires/
    index.html                  # gallery — one row per org
    questionnaire.html          # editor — ?org={slug}
    data/
      nuhw.json                 # NUHW questionnaire content
      {slug}.json               # one file per org
  protocols/
    INGEST.md                   # new questionnaire protocol
    REFRESH.md                  # update existing questionnaire
    CONVENTIONS.md              # this file
```

## JSON contract

Each `data/{slug}.json` follows this structure:

```json
{
  "slug": "nuhw",
  "org": "Full Organization Name",
  "cycle": "2026",
  "candidate": "Name — Office",
  "generated": "2026-07-22",
  "last_factcheck": "2026-07-22",
  "org_research": "2–4 sentences",
  "contact_fields": [{ "k": "key", "label": "Label", "v": "value" }],
  "questions": [{
    "id": "nuhw_q1",
    "section": "Section 2: Title",
    "topic": "controlled_topic",
    "status": "done|thin|blank|verify|blocked",
    "question": "verbatim text",
    "analysis": "research text",
    "references": [],
    "levers": [{ "tier": "authority|advocacy|unverified", "text": "..." }],
    "sources": [{ "label": "...", "url": "..." }],
    "suggested": [{ "note": "short label", "text": "draft copy" }],
    "verification": [{ "claim": "...", "result": "confirmed|refuted|unresolved", "source": "...", "date": "ISO date", "note": "..." }]
  }]
}
```

Answers are NOT stored in JSON — they go to `questionnaire_answers` in Supabase.

## Status definitions

Each question gets exactly one status:

- **`done`**: analysis, levers, and suggested copy are complete. All verification entries are `confirmed` or `refuted` (and the content reflects reality). All source URLs are live.
- **`thin`**: analysis is partial or sources are incomplete, but no unresolved blocking facts.
- **`verify`**: sources need link-checking or content re-verification.
- **`blocked`**: a load-bearing fact cannot be resolved from a primary source. The question has a verification entry with `result: "unresolved"` and a note saying what specifically needs confirming and where to look. **DO NOT generate suggested copy for blocked questions.** Blocked questions render visibly in the UI and are excluded from export until resolved.
- **`blank`**: no research has been done.

## Lever tiering

Every lever gets exactly one tier:

- **`authority`**: council has direct power (zoning, budget, ordinance, appointment). NEVER tag something authority on an assumed mechanism — each authority lever must have a verification entry confirming this jurisdiction actually has that power.
- **`advocacy`**: council can only pass resolutions, lobby, or use bully pulpit.
- **`unverified`**: mechanism has not been confirmed for this jurisdiction. Renders in a warning style. Never appears in exported drafts.

### Generic vs. named verification rule

A lever citing a **generic municipal power** (zoning, budgeting, contracting, appointments, MOUs) is low-risk — the claim is that a charter city has structural authority, which is almost always true.

A lever citing a **named ordinance, program, fund, or agency** (e.g., TOPA, a specific labor peace ordinance, a named grant program, CalPERS) requires **primary-source verification** before it can be tagged `authority`. The question is not whether such a thing could exist, but whether this jurisdiction has actually enacted or established it. Tag it `unverified` until confirmed from a primary source.

## Copy rules

- **First person.** Suggested copy is draft text the candidate submits. Write in first person: "I support…", "I would…", "my Council seat…". Use "the candidate" only in analysis, levers, notes, and other non-copy fields.
- **No gendered or second-person pronouns in non-copy fields.** Analysis, levers, and `note` labels must never use "she/her/hers," "he/him/his," or "you/your." Always use "the candidate." These fields are read by the campaign team, not the candidate — second-person address is confusing and gendered pronouns are presumptuous.
- **No hedged facts.** Suggested copy may NEVER contain an unresolved factual disjunction about the jurisdiction. Forbidden patterns: "either X or Y," "whether we use X or Y," "in most cities," and any construction that papers over something checkable. A verifiable fact is resolved, or it is omitted and flagged. It is never hedged.
- **No AI/Claude/model references.** Use neutral labels (analysis, research, strategy).
- **Asymmetric risk.** A blank answer costs nothing. A confidently wrong specific costs the endorsement and the credibility. When in doubt, leave it out and flag it.

## Controlled topic list

`why_running`, `background_bio`, `endorsement_ask`, `labor_solidarity`, `labor_law`, `healthcare_standards`, `disease_protection`, `behavioral_health`, `single_payer`, `voting_rights`, `dei_trans_care`, `cultural_competence`, `immigration`, `ice_cooperation`, `affordable_housing`, `rent_control`, `homelessness`, `campaign_plan`, `endorsements`

## Adding a new org

Follow `protocols/INGEST.md`. Key steps:
1. Create `questionnaires/data/{slug}.json`
2. Add slug to `KNOWN_ORGS` in `questionnaires/index.html`
3. Add entry to `questionnaires/data/due_dates.json`
4. Add org names to ORG_MAP in `.github/workflows/sync-due-dates.yml`
5. Optionally seed a `questionnaire_status` row

## Source documents

Original questionnaire PDFs and their Drive file IDs are tracked in `questionnaires/sources/sources.json`. The verbatim check depends on access to these source documents.

## Hosting

GitHub Pages, served from repo root. No build step, no Actions workflow. Push to `main` and it deploys.

## Rules

- No AI/Claude/model references anywhere in app output — use neutral labels (analysis, research, strategy, levers, sources, suggested)
- No API calls from the browser — all content generation happens in Claude Code sessions
- Nothing runs unattended
- Do not modify `index.html` or `setup.sql`
- Port questions verbatim — character-for-character from source, including the org's own typos
- Every authority lever must have a verification entry confirming the jurisdiction has that power
- Blocked questions get no suggested copy
- Source dates must be recorded; flag anything older than two years
- No gendered or second-person pronouns in analysis, levers, or note fields — always "the candidate"
