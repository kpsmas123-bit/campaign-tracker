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
    "status": "done|thin|blank|verify",
    "question": "verbatim text",
    "analysis": "research text",
    "references": [],
    "levers": [{ "tier": "authority|advocacy", "text": "..." }],
    "sources": [{ "label": "...", "url": "..." }],
    "suggested": [{ "note": "short label", "text": "draft copy" }]
  }]
}
```

Answers are NOT stored in JSON — they go to `questionnaire_answers` in Supabase.

## Controlled topic list

`why_running`, `background_bio`, `endorsement_ask`, `labor_solidarity`, `labor_law`, `healthcare_standards`, `disease_protection`, `behavioral_health`, `single_payer`, `voting_rights`, `dei_trans_care`, `cultural_competence`, `immigration`, `ice_cooperation`, `affordable_housing`, `rent_control`, `homelessness`, `campaign_plan`, `endorsements`

## Adding a new org

Follow `protocols/INGEST.md`. Key steps:
1. Create `questionnaires/data/{slug}.json`
2. Add slug to `KNOWN_ORGS` in `questionnaires/index.html`
3. Optionally seed a `questionnaire_status` row

## Hosting

GitHub Pages, served from repo root. No build step, no Actions workflow. Push to `main` and it deploys.

## Rules

- No AI/Claude/model references anywhere in app output — use neutral labels (analysis, research, strategy, levers, sources, suggested)
- No API calls from the browser — all content generation happens in Claude Code sessions
- Nothing runs unattended
- Do not modify `index.html` or `setup.sql`
