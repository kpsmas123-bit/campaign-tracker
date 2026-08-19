-- Google Calendar mirror — run in the Supabase SQL Editor.
--
-- One-way: Google is the source, this table is a read-only copy the calendar
-- page renders as its own layer. Kept SEPARATE from campaign_events so a sync
-- run can safely replace its whole contents without ever touching an event
-- someone created by hand on the site.
--
-- The calendar itself stays private in Google. The sync reads it through the
-- SECRET ical address, held as a GitHub Actions secret, so nothing is published
-- and no event text ever lands in this public repo.

create table if not exists gcal_events (
  -- Google's own UID for the occurrence. Recurring events expand to one row per
  -- occurrence, so the key carries the start date to keep them distinct.
  uid         text primary key,

  title       text not null default '',
  event_date  date not null,
  start_time  time,
  end_time    time,
  all_day     boolean not null default false,
  location    text not null default '',
  notes       text not null default '',

  -- Set from the feed's own timestamp so a stale sync is visible on the page
  -- rather than silently showing week-old data as current.
  synced_at   timestamptz not null default now()
);

-- Enabled immediately after create, before anything else can fail.
alter table gcal_events enable row level security;

alter table gcal_events drop constraint if exists gcal_events_len_ck;
alter table gcal_events add constraint gcal_events_len_ck
  check (
    length(title)    <= 300 and
    length(location) <= 500 and
    length(notes)    <= 5000
  );

alter table gcal_events drop constraint if exists gcal_events_time_ck;
alter table gcal_events add constraint gcal_events_time_ck
  check (end_time is null or start_time is null or end_time >= start_time);

create index if not exists gcal_events_date_idx on gcal_events (event_date);

-- Same shared campaign user as every other table here. The publishable key is
-- public by design; this policy is the only thing keeping the calendar private.
drop policy if exists "campaign_user_gcal" on gcal_events;
create policy "campaign_user_gcal"
  on gcal_events
  for all
  to authenticated
  using      (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid)
  with check (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid);

alter publication supabase_realtime add table gcal_events;

-- VERIFY. Expect rowsecurity = t and one policy with no "true" in either column.
--   select relname, relrowsecurity from pg_class where relname = 'gcal_events';
--   select policyname, qual, with_check from pg_policies where tablename = 'gcal_events';
--
-- Then, signed OUT — an empty [] is correct:
--   curl -s "https://qhrtqtnrduambvchjxqw.supabase.co/rest/v1/gcal_events?select=*" \
--     -H "apikey: sb_publishable_UAG7Ru6PRdNnOLCbchpQVg_8vE0jG5N"
