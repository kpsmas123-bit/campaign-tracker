#!/usr/bin/env python3
"""Mirror a private Google Calendar into Supabase for the calendar page.

One-way: Google is the source of truth, gcal_events is a disposable copy. The
calendar stays PRIVATE in Google; this reads it through the secret ical address,
which is a credential and must only ever live in GitHub Actions secrets.

Recurrence is expanded with recurring-ical-events rather than by hand: RRULE
plus EXDATE plus per-occurrence overrides is not something to reimplement, and
getting it subtly wrong would silently drop or duplicate real events.

Writes are made as the shared campaign user over the normal REST API, so RLS
applies exactly as it does in the browser. No service-role key is used.

Env:
  GCAL_ICS_URL        secret ical address from Google Calendar settings
  SUPABASE_URL        project url
  SUPABASE_KEY        publishable key (public by design)
  CAMPAIGN_EMAIL      shared campaign auth user
  CAMPAIGN_PASSWORD   its password
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta, timezone

import icalendar
import recurring_ical_events

# How much of the calendar to mirror. Past events are kept briefly so the month
# view still shows what just happened; the far future is bounded so a yearly
# recurring event does not expand forever.
DAYS_BACK = 120
DAYS_AHEAD = 400


def env(k, required=True):
    v = os.environ.get(k, '').strip()
    if required and not v:
        sys.exit('missing required env var: %s' % k)
    return v


def post(url, payload, headers):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else None


def parse(ics_bytes, today=None):
    """ICS -> list of row dicts, one per occurrence."""
    today = today or date.today()
    cal = icalendar.Calendar.from_ical(ics_bytes)
    start = today - timedelta(days=DAYS_BACK)
    end = today + timedelta(days=DAYS_AHEAD)

    rows, seen = [], set()
    for ev in recurring_ical_events.of(cal).between(start, end):
        if str(ev.get('STATUS', '')).upper() == 'CANCELLED':
            continue

        dtstart = ev.get('DTSTART')
        if dtstart is None:
            continue
        s = dtstart.dt
        e = ev.get('DTEND').dt if ev.get('DTEND') is not None else None

        all_day = not isinstance(s, datetime)
        if all_day:
            ev_date, st, et = s, None, None
        else:
            # Google emits tz-aware datetimes; render in the campaign's own
            # timezone so a 7pm Berkeley event is not stored as 02:00 the next
            # day. Naive values are already local.
            if s.tzinfo is not None:
                s = s.astimezone(TZ)
                if isinstance(e, datetime) and e.tzinfo is not None:
                    e = e.astimezone(TZ)
            ev_date = s.date()
            st = s.strftime('%H:%M:%S')
            et = e.strftime('%H:%M:%S') if isinstance(e, datetime) else None
            # An end before the start would violate the table's check
            # constraint; drop it rather than lose the whole event.
            if et is not None and isinstance(e, datetime) and e.date() != ev_date:
                et = None

        uid = '%s@%s' % (str(ev.get('UID', '')) or 'nouid', ev_date.isoformat())
        if uid in seen:
            continue
        seen.add(uid)

        rows.append({
            'uid': uid[:500],
            'title': str(ev.get('SUMMARY', '') or '')[:300],
            'event_date': ev_date.isoformat(),
            'start_time': st,
            'end_time': et,
            'all_day': all_day,
            'location': str(ev.get('LOCATION', '') or '')[:500],
            'notes': str(ev.get('DESCRIPTION', '') or '')[:5000],
        })
    return rows


try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('America/Los_Angeles')
except Exception:                                    # pragma: no cover
    TZ = timezone(timedelta(hours=-7))


def main():
    ics_url = env('GCAL_ICS_URL')
    sb_url = env('SUPABASE_URL').rstrip('/')
    sb_key = env('SUPABASE_KEY')
    email = env('CAMPAIGN_EMAIL')
    password = env('CAMPAIGN_PASSWORD')

    try:
        with urllib.request.urlopen(ics_url, timeout=60) as r:
            ics = r.read()
    except urllib.error.HTTPError as ex:
        sys.exit('could not fetch the calendar feed (HTTP %s). If this is 404, the '
                 'secret ical address has been reset in Google Calendar settings '
                 'and the GCAL_ICS_URL secret needs updating.' % ex.code)

    if b'BEGIN:VCALENDAR' not in ics:
        sys.exit('feed did not return an ical document; refusing to sync')

    rows = parse(ics)
    print('parsed %d occurrences' % len(rows))

    auth = post('%s/auth/v1/token?grant_type=password' % sb_url,
                {'email': email, 'password': password},
                {'apikey': sb_key, 'Content-Type': 'application/json'})
    token = auth.get('access_token')
    if not token:
        sys.exit('sign-in failed; check CAMPAIGN_EMAIL / CAMPAIGN_PASSWORD')

    h = {'apikey': sb_key, 'Authorization': 'Bearer %s' % token,
         'Content-Type': 'application/json'}

    # Upsert first, delete stale second — in that order the table is never empty,
    # so a failure halfway leaves the page showing yesterday's calendar rather
    # than an empty one.
    if rows:
        post('%s/rest/v1/gcal_events?on_conflict=uid' % sb_url, rows,
             {**h, 'Prefer': 'resolution=merge-duplicates'})

    keep = [r['uid'] for r in rows]
    req = urllib.request.Request(
        '%s/rest/v1/gcal_events?uid=not.in.(%s)'
        % (sb_url, ','.join('"%s"' % u.replace('"', '') for u in keep) or '""'),
        headers=h, method='DELETE')
    urllib.request.urlopen(req, timeout=60).read()

    print('synced %d events' % len(rows))


if __name__ == '__main__':
    main()
