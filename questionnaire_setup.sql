-- Questionnaire system tables — run in Supabase SQL Editor
-- Additive only; does not touch existing tables (tasks, team_members, campaign_settings)
--
-- BEFORE RUNNING: replace QUESTIONNAIRE_USER_UID below with the actual UUID
-- of the shared auth user (questionnaire@dariaforberkeley.com) you created
-- in Authentication > Users.

-- ============================================================
-- 1. TABLES
-- ============================================================

create table if not exists questionnaire_answers (
  id           bigint generated always as identity primary key,
  org_slug     text not null,
  question_id  text not null,
  topic        text,
  answer_text  text default '',
  approved     boolean default false,
  approved_at  timestamptz,
  is_signature boolean default false,
  updated_at   timestamptz not null default now(),
  unique (org_slug, question_id)
);

create table if not exists questionnaire_status (
  org_slug      text primary key,
  display_name  text,
  priority      text,
  category      text,
  status        text default 'not_started',
  timing        text,
  last_factcheck date,
  submitted_at  date,
  notes         text,
  updated_at    timestamptz not null default now()
);

-- ============================================================
-- 2. AUTO-TOUCH updated_at
-- ============================================================

create or replace function touch_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

drop trigger if exists t_answers on questionnaire_answers;
create trigger t_answers before update on questionnaire_answers
  for each row execute function touch_updated_at();

drop trigger if exists t_qstatus on questionnaire_status;
create trigger t_qstatus before update on questionnaire_status
  for each row execute function touch_updated_at();

-- ============================================================
-- 3. ROW-LEVEL SECURITY — locked to the shared questionnaire user
-- ============================================================
-- IMPORTANT: Replace 'QUESTIONNAIRE_USER_UID' with the real UUID.
-- Example:   '3a1b2c3d-4e5f-6789-abcd-ef0123456789'

alter table questionnaire_answers enable row level security;
alter table questionnaire_status enable row level security;

-- questionnaire_answers: only the shared auth user can read/write
create policy "questionnaire_user_answers"
  on questionnaire_answers
  for all
  using (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid)
  with check (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid);

-- questionnaire_status: only the shared auth user can read/write
create policy "questionnaire_user_status"
  on questionnaire_status
  for all
  using (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid)
  with check (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid);

-- ============================================================
-- 4. REALTIME (optional — enable if you want live updates)
-- ============================================================

alter publication supabase_realtime add table questionnaire_answers;
alter publication supabase_realtime add table questionnaire_status;
