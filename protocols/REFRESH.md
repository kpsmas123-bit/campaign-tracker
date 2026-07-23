# REFRESH — Update Existing Questionnaire

Run this protocol in a Claude Code session when updating research, sources, or suggested copy for an existing questionnaire.

## When to run

- Sources have gone stale (dead links, outdated data)
- New policy developments affect the analysis
- Candidate's platform has changed
- Fact-check cycle is due (check `last_factcheck` in the JSON)

## Steps

1. **Read the current JSON.** Open `questionnaires/data/{slug}.json`.

2. **Check all source URLs.** For each source in every question:
   - Verify the URL is still live
   - Verify the content still supports the claim
   - Replace dead links with current equivalents
   - Remove sources that can no longer be verified

3. **Update analysis.** If policy or political context has changed:
   - Revise `analysis` text to reflect current state
   - Update `levers` if council authority has changed (new ordinances, charter amendments)
   - Revise `suggested` copy to match updated analysis

4. **Re-tier levers.** Review each lever:
   - `authority`: council has direct power (zoning, budget, ordinance, appointment)
   - `advocacy`: council can only pass resolutions, lobby, or use bully pulpit
   - Remove levers that are no longer accurate

5. **Update metadata.**
   - Set `last_factcheck` to today's date
   - Update `status` on each question: `done` if fully verified, `verify` if sources need review, `thin` if analysis is incomplete

6. **Do NOT touch answers.** Answers live in Supabase, not in the JSON. Never read, copy, or modify them during a refresh.

7. **Validate the JSON.** Run `python3 -c "import json; json.load(open('questionnaires/data/{slug}.json'))"`.

8. **Commit.** The diff should show only analysis/sources/suggested changes, never structural changes to the questions array (no reordering, no merging, no renaming IDs).

## Rules

- Do not modify `question` text — that comes from the org's original questionnaire
- Do not change `id` or `topic` values — those are keys for Supabase answer lookup
- Do not reference AI, Claude, or models in any text
- Every source must be verified as live before marking a question as "done"
- Keep `generated` date unchanged — update `last_factcheck` only
