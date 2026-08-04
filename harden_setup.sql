-- SECURITY FIX — run this in the Supabase SQL Editor.
--
-- WHY: setup.sql (the original build) gave tasks, team_members and
-- campaign_settings this policy:
--
--     create policy "public access" on tasks for all using (true) with check (true);
--
-- The publishable key in the page source is public by design — that is not the
-- problem. RLS is the only control, and `using (true) with check (true)` turns
-- it off in practice. This was confirmed live: an anonymous request carrying
-- only the published key read real task rows, team member names, and campaign
-- settings, and an anonymous INSERT passed the RLS check (it failed only on a
-- primary-key collision). This is the same configuration behind the Moltbook
-- breach, where 1.5M records were exposed the same way.
--
-- It also defeats the calendar and questionnaire policies indirectly: anyone
-- could write a task, and a task name is rendered into the Tasks page, so a
-- crafted name could execute script on the site's origin and steal the shared
-- session token — which satisfies every other policy in the project.
-- (The escaping half of that chain is already fixed in index.html.)
--
-- SAFE TO RUN: all four pages authenticate as the shared campaign user before
-- reading anything, so nothing in the app loses access. No GitHub Action touches
-- these tables — donor-dashboard.yml reads a Google Sheet, and sync-due-dates.yml
-- writes a JSON file.

alter table tasks             enable row level security;
alter table team_members      enable row level security;
alter table campaign_settings enable row level security;

drop policy if exists "public access" on tasks;
drop policy if exists "public access" on team_members;
drop policy if exists "public access" on campaign_settings;

create policy "campaign_user_tasks" on tasks
  for all to authenticated
  using      (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid)
  with check (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid);

create policy "campaign_user_team" on team_members
  for all to authenticated
  using      (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid)
  with check (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid);

create policy "campaign_user_settings" on campaign_settings
  for all to authenticated
  using      (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid)
  with check (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid);

-- VERIFY — every row below must show rowsecurity = true, and no policy may
-- have "true" in qual or with_check.
--
--   select tablename, policyname, qual, with_check
--   from pg_policies
--   where tablename in ('tasks','team_members','campaign_settings','campaign_events');
--
-- Then, signed OUT, in a Terminal window (not the SQL Editor — this is a shell
-- command). An empty [] is correct; any rows mean the fix did not take:
--
--   curl -s "https://qhrtqtnrduambvchjxqw.supabase.co/rest/v1/tasks?select=*" \
--     -H "apikey: sb_publishable_UAG7Ru6PRdNnOLCbchpQVg_8vE0jG5N"
