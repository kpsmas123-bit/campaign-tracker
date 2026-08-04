// calendar-sync — pushes a campaign_events row to the dedicated Google Calendar.
//
// NOT ACTIVE UNTIL DEPLOYED. The calendar page works without this; it only adds
// the automatic path. Setup steps are in calendar/SETUP.md.
//
// Why an OAuth refresh token and not a service account: a service account
// cannot populate an event's attendee list without Workspace domain-wide
// delegation, which a personal Gmail account can never have — the request is
// rejected outright with 403 forbiddenForServiceAccounts. It would also become
// the event *organizer*, so invites would come from an address with no mailbox
// and RSVPs would have nowhere to land. Sending invites is the entire point
// here, so the token has to belong to the campaign's own account.
//
// Deploy with:  supabase functions deploy calendar-sync
// Requires config.toml:  [functions.calendar-sync]  verify_jwt = true

import { createClient } from "npm:@supabase/supabase-js@2";

const TOKEN_URL = "https://oauth2.googleapis.com/token";
const CAL_BASE = "https://www.googleapis.com/calendar/v3";

// The one shared campaign user. Same UID as the RLS policy in
// calendar_setup.sql — keep these two in sync.
const CAMPAIGN_UID = "1c6344d4-6cd5-458a-846f-cfd619d51f4a";

// Everything is local to Berkeley; sending a naive dateTime plus an explicit
// timeZone avoids a UTC round-trip and the DST bugs that come with it.
const TZ = "America/Los_Angeles";

function env(k: string): string {
  const v = Deno.env.get(k);
  if (!v) throw new Error(`missing required env var: ${k}`);
  return v;
}

const SUPABASE_URL = env("SUPABASE_URL");
const SERVICE_KEY = env("SUPABASE_SERVICE_ROLE_KEY"); // auto-injected by Supabase
const CLIENT_ID = env("GOOGLE_CLIENT_ID");
const CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET");
const REFRESH_TOKEN = env("GOOGLE_REFRESH_TOKEN");
const CALENDAR_ID = env("GOOGLE_CALENDAR_ID");
const ALLOWED_ORIGIN = Deno.env.get("ALLOWED_ORIGIN") ?? "https://hq.dariaforberkeley.com";

const cors = {
  "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Vary": "Origin",
};

const json = (b: unknown, status = 200) =>
  new Response(JSON.stringify(b), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });

const admin = createClient(SUPABASE_URL, SERVICE_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
});

// ---------------------------------------------------------------- token

let tokenCache: { value: string; expiresAt: number } | null = null;

async function getAccessToken(): Promise<string> {
  if (tokenCache && Date.now() < tokenCache.expiresAt - 60_000) return tokenCache.value;
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      refresh_token: REFRESH_TOKEN,
      grant_type: "refresh_token",
    }),
  });
  const body = await res.json();
  if (!res.ok) {
    // invalid_grant => the token was revoked, expired, or was issued while the
    // OAuth app was still in "Testing" (those expire after 7 days, permanently).
    throw new Error(`google_token_refresh_failed:${res.status}:${JSON.stringify(body)}`);
  }
  tokenCache = { value: body.access_token, expiresAt: Date.now() + body.expires_in * 1000 };
  return tokenCache.value;
}

// ---------------------------------------------------------------- google

async function gcal(
  path: string,
  init: RequestInit = {},
  query: Record<string, string> = {},
): Promise<Response> {
  const url = new URL(CAL_BASE + path);
  for (const [k, v] of Object.entries(query)) url.searchParams.set(k, v);

  for (let attempt = 0; ; attempt++) {
    const token = await getAccessToken();
    const res = await fetch(url, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
    });

    if (res.status === 401 && attempt === 0) { tokenCache = null; continue; }

    const retryable = res.status === 429 || res.status >= 500 ||
      (res.status === 403 && /rateLimitExceeded|quotaExceeded/.test(await res.clone().text()));

    if (retryable && attempt < 4) {
      await new Promise((r) =>
        setTimeout(r, Math.min(2 ** attempt * 1000 + Math.random() * 1000, 32_000)));
      continue;
    }
    return res;
  }
}

// A UUID's hex digits are a strict subset of base32hex (a-v, 0-9), so this is
// always a valid Google event id and is fully determined by the row. A retried
// insert therefore collides (409) instead of creating a duplicate event.
function googleEventId(rowId: string, seq: number): string {
  return `ev${rowId.replace(/-/g, "").toLowerCase()}v${seq}`;
}

function toGoogleEvent(row: Record<string, any>) {
  const when = row.all_day || !row.start_time
    ? {
      // Google treats an all-day end date as EXCLUSIVE.
      start: { date: row.event_date },
      end: { date: addDays(row.event_date, 1) },
    }
    : {
      start: { dateTime: `${row.event_date}T${hhmmss(row.start_time)}`, timeZone: TZ },
      end: {
        dateTime: `${row.event_date}T${hhmmss(row.end_time ?? addHour(row.start_time))}`,
        timeZone: TZ,
      },
    };

  return {
    summary: row.title,
    description: row.notes || undefined,
    location: row.location || undefined,
    ...when,
  };
}

function hhmmss(t: string): string {
  const p = String(t).split(":");
  return `${p[0].padStart(2, "0")}:${(p[1] ?? "00").padStart(2, "0")}:${(p[2] ?? "00").padStart(2, "0")}`;
}

function addHour(t: string): string {
  const p = String(t).split(":");
  return `${String((Number(p[0]) + 1) % 24).padStart(2, "0")}:${p[1] ?? "00"}`;
}

function addDays(isoDate: string, n: number): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + n));
  return dt.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------- handler

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405);

  // verify_jwt=true already rejected malformed/expired tokens at the platform
  // edge; this resolves the token to a real user and checks it is *the* user.
  const jwt = (req.headers.get("Authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!jwt) return json({ error: "missing_authorization" }, 401);

  const { data: { user }, error: authErr } = await admin.auth.getUser(jwt);
  if (authErr || !user) return json({ error: "invalid_token" }, 401);
  if (user.id !== CAMPAIGN_UID) return json({ error: "forbidden" }, 403);

  const { event_id, action } = await req.json().catch(() => ({}));
  if (!event_id || !["upsert", "delete"].includes(action)) {
    return json({ error: "bad_request" }, 400);
  }

  const { data: row, error: rowErr } = await admin
    .from("campaign_events").select("*").eq("id", event_id).single();
  if (rowErr || !row) return json({ error: "event_not_found" }, 404);

  const cal = encodeURIComponent(CALENDAR_ID);

  try {
    if (action === "delete") {
      if (row.google_event_id) {
        const res = await gcal(
          `/calendars/${cal}/events/${row.google_event_id}`,
          { method: "DELETE" },
          { sendUpdates: "all" },
        );
        // Already gone is a success, not a failure.
        if (!res.ok && ![404, 410].includes(res.status)) {
          throw new Error(`delete_failed:${res.status}:${await res.text()}`);
        }
      }
      await admin.from("campaign_events").update({
        google_event_id: null,
        sync_state: "local",
        sync_error: null,
        google_synced_at: new Date().toISOString(),
      }).eq("id", row.id);
      return json({ ok: true, action: "deleted" });
    }

    const body = toGoogleEvent(row);
    let ev: Record<string, any>;

    if (row.google_event_id) {
      const res = await gcal(
        `/calendars/${cal}/events/${row.google_event_id}`,
        { method: "PATCH", body: JSON.stringify(body) },
        { sendUpdates: "all" },
      );
      if (res.ok) {
        ev = await res.json();
      } else if ([404, 410].includes(res.status)) {
        // Deleted in the Google UI. Recreate under a fresh id.
        const seq = (row.google_id_seq ?? 0) + 1;
        ev = await insertEvent(cal, row, body, seq);
        await admin.from("campaign_events").update({ google_id_seq: seq }).eq("id", row.id);
      } else {
        throw new Error(`patch_failed:${res.status}:${await res.text()}`);
      }
    } else {
      ev = await insertEvent(cal, row, body, row.google_id_seq ?? 0);
    }

    await admin.from("campaign_events").update({
      google_event_id: ev.id,
      sync_state: "synced",
      sync_error: null,
      google_synced_at: new Date().toISOString(),
    }).eq("id", row.id);

    return json({ ok: true, google_event_id: ev.id, html_link: ev.htmlLink });
  } catch (e) {
    const msg = String(e instanceof Error ? e.message : e);
    await admin.from("campaign_events")
      .update({ sync_state: "error", sync_error: msg.slice(0, 2000) })
      .eq("id", row.id);
    console.error("calendar-sync failure", { event_id: row.id, msg });
    return json({ error: "sync_failed", detail: msg }, 502);
  }
});

async function insertEvent(
  cal: string,
  row: Record<string, any>,
  body: unknown,
  seq: number,
): Promise<Record<string, any>> {
  const id = googleEventId(row.id, seq);
  const res = await gcal(
    `/calendars/${cal}/events`,
    { method: "POST", body: JSON.stringify({ ...(body as object), id }) },
    { sendUpdates: "all" },
  );
  if (res.ok) return await res.json();

  if (res.status === 409) {
    // A previous attempt already created it; adopt rather than duplicate.
    const get = await gcal(`/calendars/${cal}/events/${id}`, { method: "GET" });
    if (get.ok) return await get.json();
  }
  throw new Error(`insert_failed:${res.status}:${await res.text()}`);
}
