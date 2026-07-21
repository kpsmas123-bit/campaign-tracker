-- Run this in Supabase SQL Editor (Dashboard > SQL Editor > New Query)

create table tasks (
  id bigint primary key,
  name text not null default '',
  done boolean not null default false,
  due text default '',
  assignee text default '',
  priority text not null default 'med'
);

create table team_members (
  id serial primary key,
  name text not null unique
);

create table campaign_settings (
  key text primary key,
  value text
);

-- Row-level security: allow all access via anon key
alter table tasks enable row level security;
alter table team_members enable row level security;
alter table campaign_settings enable row level security;

create policy "public access" on tasks for all using (true) with check (true);
create policy "public access" on team_members for all using (true) with check (true);
create policy "public access" on campaign_settings for all using (true) with check (true);

-- Enable realtime
alter publication supabase_realtime add table tasks;
alter publication supabase_realtime add table team_members;
alter publication supabase_realtime add table campaign_settings;

-- Seed data
insert into campaign_settings (key, value) values
  ('campaignName', 'City Council 2026');

insert into team_members (name) values
  ('Jordan'), ('Alex'), ('Morgan'), ('Sam');

insert into tasks (id, name, done, due, assignee, priority) values
  (1, 'Finalize yard sign locations', false, '2026-07-28', 'Jordan', 'high'),
  (2, 'Schedule candidate forum prep', false, '2026-07-25', 'Alex', 'high'),
  (3, 'Draft volunteer call script', false, '2026-07-30', 'Morgan', 'med'),
  (4, 'Update social media calendar', false, '2026-07-23', 'Sam', 'med'),
  (5, 'Order campaign mailers', true, '2026-07-20', 'Jordan', 'low'),
  (6, 'Confirm rally venue', false, '2026-08-02', 'Alex', 'high');
