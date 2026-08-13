-- Call time portal — run in the Supabase SQL Editor.
--
-- This table holds names, emails and phone numbers. Unlike task tags and
-- questionnaire order, it does NOT go in campaign_settings and it does NOT go
-- in the repo: the repo is public, and this is contact PII for people who did
-- not consent to being listed anywhere public. RLS is the only control.

create table if not exists call_contacts (
  id          uuid primary key default gen_random_uuid(),
  name        text not null default '',
  email       text not null default '',
  phone       text not null default '',

  -- Only Berkeley residents' contributions draw the 6:1 Fair Elections match,
  -- so a Berkeley $60 is worth $420 to the campaign and a non-Berkeley $60 is
  -- worth $60. This is the field that should drive call order.
  berkeley    boolean not null default false,

  -- Each attempt is {"at": "<iso timestamp>", "reached": <bool>}. An array
  -- rather than three columns so a fourth call is possible without a migration.
  attempts    jsonb not null default '[]'::jsonb,

  -- Manual, per the campaign's choice: donor records live in the Google Sheet
  -- and are deliberately not mirrored here.
  gave        boolean not null default false,
  gave_on     date,
  gave_amount numeric(8,2),

  notes       text not null default '',
  sort_order  int not null default 0,

  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

alter table call_contacts enable row level security;

-- Guard against unbounded text from a compromised client.
alter table call_contacts drop constraint if exists call_contacts_len_ck;
alter table call_contacts add constraint call_contacts_len_ck
  check (
    length(name)  <= 200 and
    length(email) <= 200 and
    length(phone) <= 60  and
    length(notes) <= 4000
  );

-- The per-donor contribution limit is $60 under the Election Reform Act, so a
-- larger figure is a data-entry error rather than good news.
alter table call_contacts drop constraint if exists call_contacts_amount_ck;
alter table call_contacts add constraint call_contacts_amount_ck
  check (gave_amount is null or (gave_amount >= 0 and gave_amount <= 60));

create index if not exists call_contacts_order_idx on call_contacts (sort_order, created_at);

drop trigger if exists t_call_contacts on call_contacts;
create trigger t_call_contacts before update on call_contacts
  for each row execute function touch_updated_at();

drop policy if exists "campaign_user_calls" on call_contacts;
create policy "campaign_user_calls"
  on call_contacts
  for all
  to authenticated
  using      (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid)
  with check (auth.uid() = '1c6344d4-6cd5-458a-846f-cfd619d51f4a'::uuid);

alter publication supabase_realtime add table call_contacts;

-- VERIFY. Expect rowsecurity = t and one policy with no "true" in either column.
--   select relname, relrowsecurity from pg_class where relname = 'call_contacts';
--   select policyname, qual, with_check from pg_policies where tablename = 'call_contacts';
--
-- Then, signed OUT, from a terminal — an empty [] is correct, any rows means
-- contact PII is being served to anyone with the published key:
--   curl -s "https://qhrtqtnrduambvchjxqw.supabase.co/rest/v1/call_contacts?select=*" \
--     -H "apikey: sb_publishable_UAG7Ru6PRdNnOLCbchpQVg_8vE0jG5N"
