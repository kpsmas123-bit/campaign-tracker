-- Questionnaire research storage — run in the Supabase SQL Editor.
--
-- WHY THIS EXISTS
-- questionnaires/data/*.json are static files served by GitHub Pages from a
-- public repo. The passphrase gate is client-side JavaScript: it hides the UI,
-- it cannot protect a file the web server hands out directly. Confirmed live —
-- /questionnaires/data/wfp.json returns HTTP 200, 176 KB, with no session.
--
-- The candidate's actual answers were never in those files (they live in
-- questionnaire_answers, correctly locked). What WAS public is the strategy
-- layer: ~204,000 characters of analysis, levers, suggested copy, and
-- per-organization research across 164 questions and 8 orgs.
--
-- This table moves that layer behind the same RLS policy as the answers. The
-- questions themselves stay in git — they are the organizations' own forms and
-- are not confidential, and keeping them in version control preserves the
-- diffable ingest history the fact-check protocol depends on.
--
-- NOTE: stripping these fields from the JSON does not remove them from git
-- history. Treat anything published before this migration as already disclosed.

create table if not exists questionnaire_research (
  org_slug    text not null,
  -- A question id, or the literal '__org__' for the organization-level
  -- research blurb (stored in `analysis`, with levers/suggested null).
  question_id text not null,
  analysis    text,
  levers      jsonb,
  suggested   jsonb,
  updated_at  timestamptz not null default now(),
  primary key (org_slug, question_id)
);

alter table questionnaire_research enable row level security;

drop policy if exists "campaign_user_research" on questionnaire_research;
create policy "campaign_user_research"
  on questionnaire_research
  for all
  to authenticated
  using      (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid)
  with check (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid);

drop trigger if exists t_research on questionnaire_research;
create trigger t_research before update on questionnaire_research
  for each row execute function touch_updated_at();

-- VERIFY (expect rowsecurity = t, one policy, no "true" in qual/with_check):
--   select relname, relrowsecurity from pg_class where relname = 'questionnaire_research';
--   select policyname, qual, with_check from pg_policies where tablename = 'questionnaire_research';
