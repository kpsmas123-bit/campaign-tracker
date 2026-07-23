# REFRESH — Update Existing Questionnaire

Run this protocol in a Claude Code session when updating research, sources, or suggested copy for an existing questionnaire.

## When to run

- Sources have gone stale (dead links, outdated data)
- New policy developments affect the analysis
- Candidate's platform has changed
- Fact-check cycle is due (check `last_factcheck` in the JSON)
- A premise about the jurisdiction has changed (city joins/leaves a program, department restructures, contract expires)

## Steps

### Mode A: Premise re-verification

Before re-checking links or updating analysis, re-run premise verification. Jurisdiction facts change: a city joins CalPERS, a program closes, a budget shifts. Re-confirm the assumptions, not only the citations.

1. **Read the current JSON.** Open `questionnaires/data/{slug}.json`.

2. **Re-verify every `verification` entry.**
   - For each entry with `result: "confirmed"`, check whether the claim still holds. Look for the latest primary source (city site, ordinance, budget, MOU, benefits guide).
   - Update the `date` field.
   - If a previously confirmed claim is now refuted, update the `result`, revise the analysis, levers, and suggested copy to reflect reality, and re-run the status check.
   - Flag any source older than two years for re-confirmation.

3. **Check for NEW premises** not previously verified. If the analysis or levers make jurisdiction-specific claims that lack a verification entry, add one and verify it now.

### Mode B: Source and content refresh

4. **Check all source URLs.** For each source in every question:
   - Verify the URL is still live
   - Verify the content still supports the claim
   - Replace dead links with current equivalents
   - Remove sources that can no longer be verified

5. **Update analysis.** If policy or political context has changed:
   - Revise `analysis` text to reflect current state
   - Update `levers` if council authority has changed (new ordinances, charter amendments)
   - Revise `suggested` copy to match updated analysis
   - Ensure suggested copy uses first person ("I support…", "I would…")
   - Ensure suggested copy contains NO hedged jurisdiction facts (see INGEST.md Copy Rules)

6. **Re-tier levers.** Review each lever:
   - `authority`: council has direct power (zoning, budget, ordinance, appointment). Must have a verification entry confirming this jurisdiction has that power.
   - `advocacy`: council can only pass resolutions, lobby, or use bully pulpit
   - `unverified`: mechanism has not been confirmed for this jurisdiction. Renders in warning style. Never appears in exported drafts.
   - Remove levers that are no longer accurate

7. **Update metadata.**
   - Set `last_factcheck` to today's date
   - Update `status` on each question per the status rules in INGEST.md step 8:
     - `done`: fully verified, all verification entries confirmed or refuted (with content reflecting reality), all URLs live
     - `thin`: partial analysis, no blocking facts
     - `verify`: sources need re-checking
     - `blocked`: load-bearing fact unresolved from primary source. NO suggested copy.
     - `blank`: no research done

8. **Do NOT touch answers.** Answers live in Supabase, not in the JSON. Never read, copy, or modify them during a refresh.

9. **Validate the JSON.** Run `python3 -c "import json; json.load(open('questionnaires/data/{slug}.json'))"`.

10. **Commit.** The diff should show only analysis/sources/suggested/verification changes, never structural changes to the questions array (no reordering, no merging, no renaming IDs).

## Rules

- Do not modify `question` text — that comes from the org's original questionnaire
- Do not change `id` or `topic` values — those are keys for Supabase answer lookup
- Do not reference AI, Claude, or models in any text
- Every source must be verified as live before marking a question as "done"
- Every authority lever must have a verification entry confirming the jurisdiction has that power
- Keep `generated` date unchanged — update `last_factcheck` only
- Blocked questions get no suggested copy
- Source dates must be recorded; flag anything older than two years
- Suggested copy must be first person and contain no hedged jurisdiction facts
