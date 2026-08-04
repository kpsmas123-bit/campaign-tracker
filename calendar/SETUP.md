# Calendar setup

The calendar page works as soon as `calendar_setup.sql` has been run. Everything
below the first section is optional and only needed for **automatic** Google
Calendar sync.

---

## 1. Required — create the table

Supabase Dashboard → SQL Editor → New Query → paste `calendar_setup.sql` → Run.

Verify RLS actually locks (this is the only thing protecting the data — the
publishable key in `calendar/index.html` is public by design):

```sql
select relname, relrowsecurity from pg_class where relname = 'campaign_events';
-- expect: campaign_events | t

select policyname, qual, with_check from pg_policies where tablename = 'campaign_events';
-- expect exactly one policy, and neither column may read "true"
```

Then confirm from a signed-out browser that an anonymous request returns nothing:

```bash
curl -s "https://qhrtqtnrduambvchjxqw.supabase.co/rest/v1/campaign_events?select=*" \
  -H "apikey: sb_publishable_UAG7Ru6PRdNnOLCbchpQVg_8vE0jG5N"
```

`[]` is correct. Any rows means the policy is wrong — stop and fix it.

That's it. The page works, and every event gets an **Add to Google Calendar**
button that opens Google prefilled.

> **Why there's a button instead of silent syncing at this stage:** the Google
> template URL has no working way to preselect a destination calendar. The `src=`
> parameter that gets copy-pasted around for this traces to a single 2009 blog
> post about the pre-2017 Calendar and is ignored today. Pick the campaign
> calendar from the dropdown on Google's page, or set up section 2.

---

## 2. Optional — automatic sync

### Why not a service account

The obvious design — a Google service account with the calendar shared to it —
**cannot send invites**, which is the whole reason for wanting this. Any
`events.insert` carrying an `attendees` array is rejected with
`403 forbiddenForServiceAccounts` unless the account has Workspace domain-wide
delegation, and a personal `@gmail.com` account can never have that. The service
account would also become the event *organizer*, so invitations would come from
an address with no mailbox.

So the credential has to be an OAuth refresh token belonging to the campaign's
own Google account, held server-side.

### 2a. Create the calendar

Google Calendar → **Other calendars → + → Create new calendar** → name it
"Campaign Events" → Create. Then **Settings → [that calendar] → Integrate
calendar** and copy the **Calendar ID** (`…@group.calendar.google.com`).

A dedicated secondary calendar keeps the blast radius small and lets you share
it read-only with staff separately.

### 2b. Google Cloud Console

1. https://console.cloud.google.com → new project.
2. **APIs & Services → Library → Google Calendar API → Enable.**
3. **Google Auth Platform → Branding** → app name + support email. User type
   **External** (the only option for a personal Gmail account).
4. **Data Access → Add scopes** → `https://www.googleapis.com/auth/calendar.events`.
   Do not use the broader `/auth/calendar` scope; it can delete whole calendars.
5. **Audience → PUBLISH APP → confirm "In production".**

   ⚠️ **Do this before step 2c.** A refresh token issued while the app is in
   "Testing" expires after **7 days**, permanently — the lifetime is stamped at
   issuance, so publishing afterwards does not rescue an existing token. This is
   the single most common way this integration silently dies.

   Publishing does **not** require Google verification here: Calendar scopes are
   "sensitive", not "restricted", and apps under 100 users are exempt. You will
   click past an "unverified app" warning once.
6. **Clients → Create client → Web application.** Under **Authorized redirect
   URIs** add exactly `https://developers.google.com/oauthplayground`.
   **Copy the client secret now** — it is masked after creation.

### 2c. Get the refresh token (once)

Signed in as the campaign Google account:

1. https://developers.google.com/oauthplayground
2. **⚙ gear → tick "Use your own OAuth credentials"** → paste client ID + secret.

   ⚠️ Not optional. Without it the Playground uses its own credentials and
   **revokes the refresh token after 24 hours**.
3. Step 1 → paste `https://www.googleapis.com/auth/calendar.events` into "Input
   your own scopes" → **Authorize APIs** → consent → **Advanced → Go to… (unsafe)**.
4. Step 2 → **Exchange authorization code for tokens** → copy the **refresh token**.

### 2d. Deploy

```bash
supabase login
supabase link --project-ref qhrtqtnrduambvchjxqw

cat > supabase/functions/.env <<'EOF'
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
GOOGLE_REFRESH_TOKEN=1//xxxxx
GOOGLE_CALENDAR_ID=xxxxx@group.calendar.google.com
ALLOWED_ORIGIN=https://hq.dariaforberkeley.com
EOF

supabase secrets set --env-file supabase/functions/.env
supabase functions deploy calendar-sync
```

`supabase/functions/.env` is already covered by `.gitignore`. **Never commit it** —
this repo is public. `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are injected
automatically; do not set them yourself, and never put the service-role key in
any file under `calendar/`.

### 2e. Turn it on in the page

In `calendar/index.html`, set:

```js
var AUTO_SYNC = true;
```

Until then the page uses the one-click button and never calls the function.

---

## 3. Operational notes

- **`invalid_grant` on refresh** means the token was revoked, expired, or was
  issued while the app was still in Testing. It lands in `campaign_events.sync_error`.
- **Six months of inactivity** kills both the refresh token and the OAuth client
  (30-day restore window). A campaign that goes quiet after the election will
  come back to a dead integration.
- **Editing or deleting** an event updates the same Google event: the function
  derives a deterministic Google event id from the row's UUID, so a retry
  collides (409) and is adopted rather than creating a duplicate. If someone
  deletes the event in Google's UI, the next edit recreates it under a fresh id.
- **Quotas** are 600 requests/min per user; a campaign creating a few dozen
  events a week is nowhere near it.

## 4. Worth doing regardless

In Dashboard → Settings → API, set **Max rows** to something like `1000`. It caps
how much any single request can pull, which limits bulk extraction if a policy is
ever loosened by mistake.
