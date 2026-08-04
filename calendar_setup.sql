-- Calendar system — run in Supabase SQL Editor
-- Additive only; does not touch tasks, team_members, campaign_settings,
-- questionnaire_answers, or questionnaire_status.
--
-- RLS is locked to the shared campaign auth user, matching the pattern in
-- questionnaire_setup.sql. It is deliberately NOT the permissive
-- `using (true)` policy used by the original setup.sql tables.

-- ============================================================
-- 1. TABLE
-- ============================================================

create table if not exists campaign_events (
  id          uuid primary key default gen_random_uuid(),
  title       text not null default '',
  event_type  text not null default 'special',
  event_date  date not null,
  start_time  time,
  end_time    time,
  all_day     boolean not null default false,
  location    text not null default '',
  notes       text not null default '',

  -- Google Calendar linkage. Populated once an event is pushed across;
  -- lets a later edit update the same event instead of duplicating it.
  -- Unused until the calendar-sync Edge Function is deployed (see
  -- calendar/SETUP.md); the one-click "Add to Google Calendar" button needs none
  -- of this.
  google_event_id  text,
  google_synced_at timestamptz,
  -- Bumped when an event has to be recreated because someone deleted it in
  -- Google: deleted Google event ids cannot be reliably reused.
  google_id_seq    int not null default 0,
  sync_state       text not null default 'local'
                   check (sync_state in ('local','pending','synced','error')),
  sync_error       text,

  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Enabled IMMEDIATELY after create, before any other DDL. Postgres creates
-- tables with RLS off, so if this file is ever run partially -- an error
-- midway, or someone pasting one section at a time -- the table must never
-- exist in a readable state. Everything below is safe to fail; this is not.
alter table campaign_events enable row level security;

-- Controlled vocabulary: a bad event_type would render as an unstyled pill,
-- so reject it at the database rather than papering over it in the UI.
alter table campaign_events drop constraint if exists campaign_events_type_ck;
alter table campaign_events add constraint campaign_events_type_ck
  check (event_type in (
    'house_party', 'canvass', 'endorsement',
    'special', 'internal', 'deadline'
  ));

-- Guard against unbounded text from a compromised client.
alter table campaign_events drop constraint if exists campaign_events_len_ck;
alter table campaign_events add constraint campaign_events_len_ck
  check (
    length(title)    <= 200 and
    length(location) <= 300 and
    length(notes)    <= 5000
  );

-- An end time before the start time is always a mistake.
alter table campaign_events drop constraint if exists campaign_events_time_ck;
alter table campaign_events add constraint campaign_events_time_ck
  check (end_time is null or start_time is null or end_time >= start_time);

create index if not exists campaign_events_date_idx
  on campaign_events (event_date);

-- ============================================================
-- 2. AUTO-TOUCH updated_at
-- ============================================================
-- touch_updated_at() already exists from questionnaire_setup.sql; this
-- recreates it defensively so this file can be run standalone.

create or replace function touch_updated_at() returns trigger
  language plpgsql
  security invoker
  set search_path = ''
as $$
begin new.updated_at = now(); return new; end;
$$;

drop trigger if exists t_campaign_events on campaign_events;
create trigger t_campaign_events before update on campaign_events
  for each row execute function touch_updated_at();

-- ============================================================
-- 3. ROW-LEVEL SECURITY — locked to the shared campaign user
-- ============================================================
-- Same UID as questionnaire_setup.sql. The publishable key is public by
-- design; this policy is what actually keeps the table private, so an
-- anonymous request with that key reads zero rows.

drop policy if exists "campaign_user_events" on campaign_events;
create policy "campaign_user_events"
  on campaign_events
  for all
  to authenticated
  using      (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid)
  with check (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid);

-- ============================================================
-- 4. REALTIME
-- ============================================================

alter publication supabase_realtime add table campaign_events;

-- ============================================================
-- 5. VERIFY  (expect: rowsecurity = true, one policy, zero permissive rows)
-- ============================================================
-- select relname, relrowsecurity from pg_class where relname = 'campaign_events';
-- select policyname, qual, with_check from pg_policies where tablename = 'campaign_events';
