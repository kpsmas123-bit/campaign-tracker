"""Generate the static fundraising dashboard from aggregated donor data.

donors/index.html is a BUILD ARTIFACT owned by the donor-dashboard workflow.
Do not regenerate it from a scratch/test JSON and commit that — doing so
overwrites the Action's output and freezes a stale "Updated" date on the live
page. After changing this file, trigger the workflow instead:
    gh workflow run donor-dashboard.yml --ref main

Berkeley public financing rules encoded here are verified against the City of
Berkeley Public Financing Program Guide and the 2026 disbursement tracker:
  - 6:1 match on qualifying contributions of up to $60
  - Only contributions from Berkeley residents qualify
  - City Council cap is $52,000 in total matching funds
"""
import json, sys, html, math

# ── Auth gate ────────────────────────────────────────────────────────
# Same Supabase passphrase wall as Tasks and Questionnaires, so the site
# behaves consistently. Note this is a UX gate, not a confidentiality
# control: this repo is public, so the aggregates below are readable from
# the repo itself regardless. Never put donor PII in this file.
# Kept as plain strings (not f-strings) so JS/CSS braces need no escaping.

AUTH_CSS = """
  .auth-gate {
    min-height: calc(100vh - 52px); display: flex;
    align-items: center; justify-content: center; padding: 24px;
  }
  .auth-card {
    max-width: 340px; width: 100%;
    display: flex; flex-direction: column; gap: 14px;
  }
  .auth-title {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 20px; font-weight: normal;
  }
  .auth-sub { font-size: 13px; color: var(--text-secondary); line-height: 1.5; }
  .auth-input {
    font-family: inherit; font-size: 14px; color: var(--text);
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 3px; padding: 10px 12px; width: 100%; outline: none;
  }
  .auth-input:focus { border-color: var(--accent); }
  .auth-btn {
    font-family: inherit; font-size: 13px; font-weight: 500;
    color: var(--surface); background: var(--accent);
    border: 1px solid var(--accent); border-radius: 3px;
    padding: 10px 16px; cursor: pointer; width: 100%;
  }
  .auth-btn:hover { background: var(--accent-hover); }
  .auth-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .auth-error { font-size: 13px; color: var(--priority-high); line-height: 1.5; }
"""

AUTH_HTML = """
<div class="auth-gate" id="authGate">
  <div class="auth-card">
    <div class="auth-title">Daria for Berkeley</div>
    <div class="auth-sub">Enter the campaign passphrase to continue.</div>
    <input class="auth-input" id="authPass" type="password" placeholder="Passphrase" autocomplete="current-password">
    <button class="auth-btn" id="authBtn">Sign in</button>
    <div class="auth-error" id="authError" style="display:none"></div>
  </div>
</div>
"""

AUTH_JS = """
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
<script>
(function () {
  var SUPABASE_URL = 'https://qhrtqtnrduambvchjxqw.supabase.co';
  var SUPABASE_KEY = 'sb_publishable_UAG7Ru6PRdNnOLCbchpQVg_8vE0jG5N';
  var AUTH_EMAIL = 'questionnaire@dariaforberkeley.com';
  var sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

  var authGate = document.getElementById('authGate');
  var authPass = document.getElementById('authPass');
  var authBtn = document.getElementById('authBtn');
  var authError = document.getElementById('authError');
  var appRoot = document.getElementById('appRoot');
  var siteNav = document.getElementById('siteNav');

  function reveal() {
    authGate.style.display = 'none';
    siteNav.style.display = '';
    appRoot.style.display = 'block';
  }
  function showErr(m) { authError.textContent = m; authError.style.display = 'block'; }

  async function doAuth() {
    var pass = authPass.value.trim();
    if (!pass) { showErr('Enter the passphrase.'); return; }
    authBtn.disabled = true; authBtn.textContent = 'Signing in...';
    try {
      var res = await sb.auth.signInWithPassword({ email: AUTH_EMAIL, password: pass });
      if (res.error) throw res.error;
      reveal();
    } catch (e) {
      authBtn.disabled = false; authBtn.textContent = 'Sign in';
      showErr('Wrong passphrase.');
    }
  }

  authBtn.addEventListener('click', doAuth);
  authPass.addEventListener('keydown', function (e) { if (e.key === 'Enter') doAuth(); });
  sb.auth.getSession().then(function (r) {
    if (r.data && r.data.session) reveal();
  });
})();
</script>
"""


ELECTION_DAY = '2026-11-03'


def pace_html(qual_left, bky_avg, history, max_gift=60):
    """What it takes per day, from today until Election Day, to max the match.

    Days are counted from today (inclusive) up to Election Day (exclusive), so
    on Nov 2 there is one day left. The page is built once a day, so a small
    script re-counts the days from the viewer's Pacific date and re-divides —
    the remaining dollars only change when the sheet does.

    Recent pace comes from the History tab: qualifying dollars gained over the
    last seven days of snapshots, as a daily rate.
    """
    from datetime import date, datetime, timedelta, timezone

    election = date.fromisoformat(ELECTION_DAY)
    # Pacific date at build time (UTC-7 through Nov 1; close enough for a count)
    today = (datetime.now(timezone.utc) - timedelta(hours=7)).date()
    days = max(0, (election - today).days)

    if qual_left <= 0:
        return ''

    # Last-7-days pace from the daily snapshots
    pace = None
    pts = []
    for h in history or []:
        try:
            pts.append((date.fromisoformat(str(h['date'])[:10]), float(h.get('qualifying') or 0)))
        except (KeyError, TypeError, ValueError):
            continue
    pts.sort()
    if len(pts) >= 2:
        end_d, end_q = pts[-1]
        base = [p for p in pts if p[0] <= end_d - timedelta(days=7)]
        if base:
            b_d, b_q = base[-1]
            span = (end_d - b_d).days
            if span > 0:
                pace = max(0.0, (end_q - b_q) / span)

    avg = bky_avg if bky_avg else max_gift

    if days <= 0:
        per_day = qual_left
    else:
        per_day = qual_left / days
    gifts_avg = per_day / avg
    gifts_max = per_day / max_gift

    if pace is None:
        pace_line = ''
    else:
        on_pace = pace >= per_day
        cls = 'good' if on_pace else 'behind'
        icon = '&#10003;' if on_pace else '&#9888;'
        word = 'On pace' if on_pace else 'Behind pace'
        pace_line = (
            f'<div class="pace-status {cls}" id="paceStatus">'
            f'<span class="pace-icon" aria-hidden="true">{icon}</span>'
            f'<b id="paceWord">{word}</b> &mdash; the last 7 days brought in '
            f'{money(pace)} a day from Berkeley residents'
            f'<span id="paceGap">{"" if on_pace else " (" + money(per_day - pace) + " a day short)"}</span>.'
            '</div>'
        )

    js = PACE_JS.replace('__DATA__', json.dumps({
        'election': ELECTION_DAY, 'left': round(qual_left, 2), 'avg': round(avg, 2),
        'max': max_gift, 'pace': None if pace is None else round(pace, 2),
    }))

    return f"""
  <div class="card">
    <div class="card-title">Daily goal &mdash; max the match by Nov 3</div>
    <div class="figures three">
      <div class="figure">
        <div class="figure-value" id="paceDays">{days}</div>
        <div class="figure-label">days until Election Day</div>
        <div class="figure-note">counting today</div>
      </div>
      <div class="figure">
        <div class="figure-value" id="paceDollars">{money(per_day)}</div>
        <div class="figure-label">in qualifying gifts a day</div>
        <div class="figure-note">{money(qual_left)} still to go</div>
      </div>
      <div class="figure">
        <div class="figure-value" id="paceGifts">{gifts_avg:.1f}</div>
        <div class="figure-label">qualifying gifts a day</div>
        <div class="figure-note">at the {money(avg, cents=True)} Berkeley average &middot; <span id="paceWeek">{gifts_avg * 7:.0f}</span> a week</div>
      </div>
    </div>
    {pace_line}
  </div>
{js}"""


PACE_JS = """
<script>
(function () {
  var D = __DATA__;
  function money(n) { return '$' + Math.round(n).toLocaleString('en-US'); }
  // Today's date in Berkeley, whatever the viewer's clock zone
  var parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Los_Angeles',
    year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
  var today = Date.UTC(+parts.slice(0, 4), +parts.slice(5, 7) - 1, +parts.slice(8, 10));
  var e = D.election.split('-');
  var days = Math.max(0, Math.round((Date.UTC(+e[0], +e[1] - 1, +e[2]) - today) / 864e5));
  var perDay = days > 0 ? D.left / days : D.left;
  var gifts = perDay / D.avg;
  function set(id, t) { var n = document.getElementById(id); if (n) n.textContent = t; }
  set('paceDays', days);
  set('paceDollars', money(perDay));
  set('paceGifts', gifts.toFixed(1));
  set('paceWeek', Math.round(gifts * 7));
  if (D.pace !== null) {
    var ok = D.pace >= perDay, box = document.getElementById('paceStatus');
    if (box) {
      box.className = 'pace-status ' + (ok ? 'good' : 'behind');
      box.querySelector('.pace-icon').innerHTML = ok ? '&#10003;' : '&#9888;';
      set('paceWord', ok ? 'On pace' : 'Behind pace');
      set('paceGap', ok ? '' : ' (' + money(perDay - D.pace) + ' a day short)');
    }
  }
})();
</script>
"""


def money(n, cents=False):
    return f"${n:,.2f}" if cents else f"${n:,.0f}"


def pct(n, d):
    return min(100.0, (n / d * 100)) if d else 0.0


def delta_html(now, before, as_money=True):
    """Week-over-week change chip. Returns '' when there's no prior snapshot."""
    if before in (None, '', 0) and before != 0:
        return '<span class="delta none">no prior week</span>'
    try:
        before = float(before)
    except (TypeError, ValueError):
        return '<span class="delta none">no prior week</span>'
    diff = now - before
    if abs(diff) < 0.005:
        return '<span class="delta flat">no change this week</span>'
    arrow = '&uarr;' if diff > 0 else '&darr;'
    cls = 'up' if diff > 0 else 'down'
    val = money(abs(diff)) if as_money else f"{abs(diff):,.0f}"
    return f'<span class="delta {cls}">{arrow} {val} this week</span>'


def _nice_scale(v, target=4):
    """A clean tick step and the axis top it implies.

    Chosen step-first: rounding the top and then dividing it into equal parts
    is how a $1,500 axis ends up with ticks every $375. Picking the step from
    1/2/2.5/5 first guarantees every gridline lands on a round number, and the
    top is simply the first multiple of that step at or above the data.
    """
    if v <= 0:
        return 1000, 250
    raw = v / target
    mag = 10 ** int(math.floor(math.log10(raw)))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    top = step * math.ceil(v / step)
    return top, step


TIMELINE_JS = """
<script>
(function () {
  var pts = __SERIES__;
  var wrap = document.getElementById('tlLine');
  if (!wrap) return;
  var svg = wrap.querySelector('svg'), tip = document.getElementById('tlTip');
  var cross = document.getElementById('tlCross'), hit = document.getElementById('tlHit');
  var W = __W__;
  function fmt(v) { return '$' + Math.round(v).toLocaleString(); }
  function show(evt) {
    var r = svg.getBoundingClientRect();
    var sx = (evt.clientX - r.left) * (W / r.width), best = pts[0];
    for (var i = 1; i < pts.length; i++)
      if (Math.abs(pts[i].x - sx) < Math.abs(best.x - sx)) best = pts[i];
    cross.setAttribute('x1', best.x); cross.setAttribute('x2', best.x);
    cross.setAttribute('visibility', 'visible');
    tip.innerHTML = '<div class="d">' + best.d + '</div>' +
      '<div><span class="k" style="background:var(--series-total)"></span>' + fmt(best.t) + ' raised</div>' +
      '<div><span class="k" style="background:var(--series-bky)"></span>' + fmt(best.b) + ' matchable</div>' +
      '<div class="d">' + best.n + ' donors</div>';
    tip.hidden = false;
    var wr = wrap.getBoundingClientRect(), px = best.x / W * wr.width;
    var left = px + 12;
    if (left + tip.offsetWidth > wr.width) left = px - tip.offsetWidth - 12;
    tip.style.left = Math.max(0, left) + 'px';
    tip.style.top = '8px';
  }
  function hide() { cross.setAttribute('visibility', 'hidden'); tip.hidden = true; }
  hit.addEventListener('mousemove', show);
  hit.addEventListener('mouseleave', hide);
  hit.addEventListener('touchstart', function (e) { show(e.touches[0]); }, { passive: true });

  var bw = document.getElementById('tlBars');
  if (!bw) return;
  var btip = document.getElementById('tlBarTip');
  bw.querySelectorAll('.tl-col').forEach(function (c) {
    c.addEventListener('mouseenter', function () {
      btip.textContent = c.getAttribute('data-tip');
      btip.hidden = false;
      var br = bw.getBoundingClientRect(), cr = c.getBoundingClientRect();
      var left = cr.left - br.left + cr.width / 2 - btip.offsetWidth / 2;
      btip.style.left = Math.max(0, Math.min(left, br.width - btip.offsetWidth)) + 'px';
      btip.style.top = (cr.top - br.top - btip.offsetHeight - 8) + 'px';
    });
    c.addEventListener('mouseleave', function () { btip.hidden = true; });
  });
})();
</script>"""


def timeline_html(history):
    """Cumulative raised over time, and new money by week.

    Built from the History tab's daily snapshots -- aggregates only, no donor
    names, which matters because this file is committed to a public repo.

    Two charts rather than one, because the running total and a week's new
    money differ by an order of magnitude: on a shared axis the weekly bars
    would be a flat line along the bottom, and a second y-axis would invite
    reading the two against each other in a way that means nothing.
    """
    from datetime import date, timedelta

    pts = []
    for h in history or []:
        try:
            dd = date.fromisoformat(str(h['date'])[:10])
            pts.append({'d': dd, 'total': float(h['total_raised']),
                        'bky': float(h.get('qualifying') or 0),
                        'donors': int(float(h.get('unique_donors') or 0))})
        except (KeyError, TypeError, ValueError):
            continue
    pts.sort(key=lambda p: p['d'])
    if len(pts) < 2:
        return ''

    # --- cumulative chart ------------------------------------------------
    W, H = 640, 240
    L, R, T, B = 56, 16, 22, 26
    pw, ph = W - L - R, H - T - B
    d0, d1 = pts[0]['d'], pts[-1]['d']
    span = max((d1 - d0).days, 1)
    top, step = _nice_scale(max(p['total'] for p in pts), 4)

    # A true time axis, not evenly spaced points: the snapshot feed skipped a
    # couple of days, and index spacing would quietly stretch those weeks.
    def X(dd):
        return L + pw * (dd - d0).days / span

    def Y(v):
        return T + ph * (1 - v / top)

    out = []
    for i in range(int(round(top / step)) + 1):
        v = step * i
        y = Y(v)
        out.append('<line class="%s" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>'
                   % ('tl-base' if i == 0 else 'tl-grid', L, W - R, y, y))
        out.append('<text class="tl-tick" x="%d" y="%.1f" text-anchor="end" dy="3">%s</text>'
                   % (L - 8, y, money(v)))

    # A label at the first of each month in range. The start date lives in the
    # note beneath instead of on the axis, where it crowded out August.
    m = date(d0.year, d0.month, 1)
    while m <= d1:
        if m >= d0:
            out.append('<text class="tl-tick" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                       % (X(m), H - 8, m.strftime('%b')))
        m = date(m.year + (m.month // 12), m.month % 12 + 1, 1)

    def path(key):
        return 'M' + ' L'.join('%.1f,%.1f' % (X(p['d']), Y(p[key])) for p in pts)

    area = path('total') + ' L%.1f,%.1f L%.1f,%.1f Z' % (X(d1), Y(0), X(d0), Y(0))
    out.append('<path d="%s" fill="var(--series-total)" fill-opacity="0.10" stroke="none"/>' % area)
    out.append('<path class="tl-line" d="%s" stroke="var(--series-bky)"/>' % path('bky'))
    out.append('<path class="tl-line" d="%s" stroke="var(--series-total)"/>' % path('total'))

    last = pts[-1]
    # Endpoint values only -- the headline figures -- with the axis and the
    # hover tooltip carrying everything in between.
    for key, var, dy, base in (('bky', '--series-bky', 10, 'hanging'),
                               ('total', '--series-total', -10, 'auto')):
        out.append('<circle class="tl-dot" cx="%.1f" cy="%.1f" r="4" fill="var(%s)"/>'
                   % (X(last['d']), Y(last[key]), var))
        # "hanging" puts the text below its anchor whatever its size, so the
        # lower label clears its own line at phone scale as well as desktop.
        out.append('<text class="tl-end" x="%.1f" y="%.1f" text-anchor="end" dx="-8" dy="%d" '
                   'dominant-baseline="%s">%s</text>'
                   % (X(last['d']), Y(last[key]), dy, base, money(last[key])))

    out.append('<line class="tl-cross" id="tlCross" x1="0" x2="0" y1="%d" y2="%d" visibility="hidden"/>'
               % (T, H - B))
    out.append('<rect id="tlHit" x="%d" y="%d" width="%d" height="%d" fill="transparent"/>'
               % (L, T, pw, ph))

    series_json = json.dumps([{'x': round(X(p['d']), 1),
                               'd': p['d'].strftime('%b ') + str(p['d'].day),
                               't': p['total'], 'b': p['bky'], 'n': p['donors']} for p in pts])

    # --- weekly new money ------------------------------------------------
    # The last snapshot in each Monday-start week, differenced against the week
    # before. The first week has no prior figure and so no bar: its balance is
    # money raised before tracking began, not money raised that week.
    weeks = {}
    for p in pts:
        wk = p['d'] - timedelta(days=p['d'].weekday())
        weeks[wk] = p
    wk_keys = sorted(weeks)
    bars = []
    for prev, cur in zip(wk_keys, wk_keys[1:]):
        bars.append({'wk': cur, 'amt': weeks[cur]['total'] - weeks[prev]['total'],
                     'donors': weeks[cur]['donors'] - weeks[prev]['donors'],
                     'partial': False})
    # Only the final week can be in progress. Testing each week for a Sunday
    # snapshot instead wrongly flags finished weeks whose Sunday the feed
    # happened to skip — the week of Aug 10 was marked unfinished that way.
    # Left unmarked, the real in-progress week reads as money drying up.
    if bars:
        bars[-1]['partial'] = pts[-1]['d'] < bars[-1]['wk'] + timedelta(days=6)

    def wk_label(dd):
        return dd.strftime('%b ') + str(dd.day)

    bars_html = ''
    if bars:
        BW, BH = 640, 150
        bL, bR, bT, bB = 56, 16, 22, 24
        bpw, bph = BW - bL - bR, BH - bT - bB
        btop, bstep = _nice_scale(max(max(b['amt'] for b in bars), 1), 3)
        band = bpw / len(bars)
        colw = min(24, band * 0.6)

        def BY(v):
            return bT + bph * (1 - max(v, 0) / btop)

        b_out = []
        n_ticks = int(round(btop / bstep))
        for i in range(n_ticks + 1):
            v = bstep * i
            y = BY(v)
            b_out.append('<line class="%s" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>'
                         % ('tl-base' if i == 0 else 'tl-grid', bL, BW - bR, y, y))
            mid = ' tl-mid' if 0 < i < n_ticks else ''
            b_out.append('<text class="tl-tick%s" x="%d" y="%.1f" text-anchor="end" dy="3">%s</text>'
                         % (mid, bL - 8, y, money(v)))
        for i, b in enumerate(bars):
            cx = bL + band * i + (band - colw) / 2
            yt, yb = BY(b['amt']), BY(0)
            r = max(0, min(4, yb - yt, colw / 2))
            # rounded data-end, square at the baseline
            d = ('M%.1f,%.1f L%.1f,%.1f Q%.1f,%.1f %.1f,%.1f L%.1f,%.1f '
                 'Q%.1f,%.1f %.1f,%.1f L%.1f,%.1f Z'
                 % (cx, yb, cx, yt + r, cx, yt, cx + r, yt, cx + colw - r, yt,
                    cx + colw, yt, cx + colw, yt + r, cx + colw, yb))
            tip = 'Week of %s: %s from %d new donor%s%s' % (
                wk_label(b['wk']), money(b['amt']), b['donors'], '' if b['donors'] == 1 else 's',
                ' (week in progress)' if b['partial'] else '')
            b_out.append('<path class="tl-col%s" d="%s" data-tip="%s"><title>%s</title></path>'
                         % (' partial' if b['partial'] else '', d, html.escape(tip), html.escape(tip)))
            b_out.append('<text class="tl-tick" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                         % (cx + colw / 2, BH - 6, '%d/%d' % (b['wk'].month, b['wk'].day)))
        # value on the cap of the latest week only -- the one being asked about
        lb = bars[-1]
        # Right-aligned to the plot edge: centred on the last column, a longer
        # label like "$340 so far" ran off the side of the chart.
        b_out.append('<text class="tl-end" x="%d" y="%.1f" text-anchor="end" dy="-7">%s%s</text>'
                     % (BW - bR, BY(lb['amt']), money(lb['amt']), ' so far' if lb['partial'] else ''))
        bar_aria = 'New money by week; most recently %s in the week of %s' % (
            money(lb['amt']), wk_label(lb['wk']))
        bars_html = ('<div class="tl-sub">New money by week</div>'
                     '<div class="tl-chart" id="tlBars">'
                     '<svg viewBox="0 0 %d %d" role="img" aria-label="%s">%s</svg>'
                     '<div class="tl-tip" id="tlBarTip" hidden></div></div>'
                     % (BW, BH, html.escape(bar_aria), ''.join(b_out)))

    rows = ''.join('<tr><td>%s%s</td><td>%s</td><td>%s</td><td>%d</td></tr>'
                   % (wk_label(b['wk']), ' (so far)' if b['partial'] else '', money(b['amt']),
                      money(weeks[b['wk']]['total']), b['donors']) for b in reversed(bars))

    aria = ('Total raised rose from %s on %s to %s on %s; Berkeley matchable contributions reached %s.'
            % (money(pts[0]['total']), wk_label(d0), money(last['total']),
               wk_label(d1), money(last['bky'])))

    card = (
        '\n  <div class="card">'
        '\n    <div class="tl-head">'
        '\n      <div class="card-title" style="margin-bottom:0">Donation timeline</div>'
        '\n      <div class="tl-legend">'
        '\n        <span class="tl-key"><span class="tl-swatch" style="background:var(--series-total)"></span>Total raised</span>'
        '\n        <span class="tl-key"><span class="tl-swatch" style="background:var(--series-bky)"></span>Berkeley matchable</span>'
        '\n      </div>'
        '\n    </div>'
        '\n    <div class="tl-chart" id="tlLine">'
        '\n      <svg viewBox="0 0 %d %d" role="img" aria-label="%s">%s</svg>'
        '\n      <div class="tl-tip" id="tlTip" hidden></div>'
        '\n    </div>'
        '\n    %s'
        '\n    <div class="tl-note">Tracking began %s with %s already raised, so that opening balance is not attributed to any week.</div>'
        '\n    <details class="tl-table">'
        '\n      <summary>Show weekly figures as a table</summary>'
        '\n      <table><thead><tr><th>Week of</th><th>New money</th><th>Running total</th><th>New donors</th></tr></thead>'
        '\n      <tbody>%s</tbody></table>'
        '\n    </details>'
        '\n  </div>'
    ) % (W, H, html.escape(aria), ''.join(out), bars_html,
         wk_label(d0), money(pts[0]['total']), rows)

    return card + TIMELINE_JS.replace('__SERIES__', series_json).replace('__W__', str(W))


def generate(data_path, out_path):
    with open(data_path) as f:
        d = json.load(f)

    total     = d['total_raised']
    donors    = d['unique_donors']
    count     = d['donation_count']
    avg       = d['average_donation']
    updated   = str(d.get('updated', ''))[:10]

    # `updated` is the BUILD time — it says the workflow ran, not that the
    # numbers moved. Those are different claims, and conflating them is how a
    # nine-day stall in the ActBlue feed stayed invisible: the page said
    # "Updated <today>" every single day while publishing July 28's figures.
    # This reports the age of the underlying reports instead.
    age = d.get('data_age_days', None)
    through = str(d.get('newest_report_date', ''))[:10]
    if age is None or age < 0:
        freshness = ' &middot; <span class="freshness dead">no report data</span>'
    elif age <= 1:
        freshness = (' &middot; data through %s' % through) if through else ''
    else:
        cls = 'dead' if age >= 7 else 'stale'
        label = '%d days old' % age
        if through:
            label = 'data through %s &mdash; %d days old' % (through, age)
        freshness = ' &middot; <span class="freshness %s">%s</span>' % (cls, label)

    bky_raised = d.get('berkeley_raised', 0)
    bky_count  = d.get('berkeley_donations', 0)
    qualifying = d.get('qualifying', 0)
    match      = d.get('match_earned', 0)
    match_left = d.get('match_remaining', 0)
    match_cap  = d.get('match_cap', 52000)
    ratio      = d.get('match_ratio', 6)
    projected  = d.get('projected_total', total + match)
    timeline   = timeline_html(d.get('history', []))

    week_total  = d.get('week_ago_total', '')
    week_donors = d.get('week_ago_donors', '')

    # Certification: no matching funds are paid until the threshold is met, so
    # until then the match is a projection, not money earned.
    certified   = bool(d.get('is_certified', False))
    qual_ctrb   = int(d.get('qualified_contributors', 0))
    qual_min    = int(d.get('qualify_min_count', 30))
    cert_short  = int(d.get('certify_short', max(0, qual_min - qual_ctrb)))

    match_word  = 'earned' if certified else 'projected'
    match_label = 'Matching funds earned' if certified else 'Matching funds projected'

    if certified:
        cert_banner = ''
    else:
        plural = 'contributor' if cert_short == 1 else 'contributors'
        cert_banner = (
            '<div class="alert">'
            f'<b>Not yet certified &mdash; {cert_short} more qualifying {plural} needed.</b> '
            f'The program requires {qual_min} contributors giving $10&ndash;$60 each; '
            f'you have {qual_ctrb}. No matching funds are paid until that is met, '
            'so the figures below are projections.'
            '</div>'
        )

    # Qualifying contributions needed to max out the match
    qual_needed = match_cap / ratio
    qual_left   = max(0.0, qual_needed - qualifying)

    match_pct = pct(match, match_cap)
    qual_pct  = pct(qualifying, qual_needed)

    # Share of money raised that is match-eligible
    bky_share = (qualifying / total * 100) if total else 0.0

    # Share of donors who are Berkeley residents. Falls back to the share of
    # donations if an older Summary tab has no berkeley_donors row yet.
    bky_donors = d.get('berkeley_donors') or 0
    if bky_donors and donors:
        donor_share = bky_donors / donors * 100
    else:
        bky_donors = bky_count
        donor_share = (bky_count / count * 100) if count else 0.0

    # How many more Berkeley gifts to max the match.
    # $60 is the ceiling on what counts, so gifts_at_max is the floor on the
    # number needed; the average-gift figure is the realistic expectation.
    max_gift    = 60
    gifts_at_max = math.ceil(qual_left / max_gift) if qual_left > 0 else 0
    bky_avg      = (qualifying / bky_count) if bky_count else 0
    gifts_at_avg = math.ceil(qual_left / bky_avg) if (qual_left > 0 and bky_avg) else 0

    if qual_left <= 0:
        countdown_value = 'Maxed'
        countdown_label = 'the match is fully earned'
        countdown_note  = 'further Berkeley gifts add no matching funds'
    else:
        countdown_value = f'{gifts_at_max:,}'
        countdown_label = f'more {money(max_gift)} gifts max the match'
        if gifts_at_avg:
            countdown_note = (f'about {gifts_at_avg:,} at the current '
                              f'{money(bky_avg, cents=True)} Berkeley average '
                              f'&middot; {money(qual_left)} to go')
        else:
            countdown_note = f'{money(qual_left)} still needed from Berkeley residents'

    pace = pace_html(qual_left, bky_avg, d.get('history', []), max_gift)

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow, noarchive">
<title>Fundraising &middot; Campaign Tracker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --ground: #F9F9F6;
    --surface: #FFFFFF;
    --text: #2A2A2E;
    --text-secondary: #7C7C82;
    --text-tertiary: #A8A8AC;
    --border: #E6E6E2;
    --border-light: #F0F0EC;
    --accent: #4A6FA5;
    --accent-hover: #3D5E8C;
    --priority-high: #C45240;
    --priority-medium: #C89B2A;
    --priority-medium-bg: #C89B2A12;
    --priority-low: #6B956B;
    --team-bg: #F2F2EE;
    --hover: #F4F4F0;
    /* Chart series. Validated against the card surface in each theme for
       lightness band, chroma floor, colour-blind separation and contrast —
       the app accent is too desaturated to read as a data mark, so these are
       the same hues pushed just far enough to pass. Status colours (the gold,
       green and red above) are never used for a series. */
    --series-total: #3868B0;
    --series-bky: #C57542;
  }}

  @media (prefers-color-scheme: dark) {{
    :root {{
      --ground: #18181B;
      --surface: #1E1E22;
      --text: #E4E4E0;
      --text-secondary: #8E8E92;
      --text-tertiary: #5A5A5E;
      --border: #2E2E32;
      --border-light: #262628;
      --accent: #6B8FC4;
      --accent-hover: #7DA0D0;
      --priority-high: #D4705F;
      --priority-medium: #D4AD4A;
      --priority-medium-bg: #D4AD4A18;
      --priority-low: #7DAF7D;
      --team-bg: #222226;
      --hover: #24242A;
      --series-total: #6293DB;
      --series-bky: #C97D4C;
    }}
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: var(--ground);
    color: var(--text);
    font-family: system-ui, -apple-system, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }}

  .site-nav {{
    display: flex; align-items: center; gap: 2px;
    max-width: 860px; margin: 0 auto;
    padding: 16px 24px 0;
  }}
  .site-nav a {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--text-tertiary); text-decoration: none;
    padding: 5px 10px; border-bottom: 2px solid transparent;
  }}
  .site-nav a:hover {{ color: var(--text-secondary); }}
  .site-nav a.active {{ color: var(--text); border-bottom-color: var(--accent); }}

  .app {{ max-width: 860px; margin: 0 auto; padding: 40px 24px 80px; }}

  .page-title {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 22px; font-weight: normal; margin-bottom: 4px;
  }}
  .page-sub {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--text-tertiary); margin-bottom: 28px;
  }}
  /* Data freshness, distinct from build time. A stale figure and a live one
     look identical, which is how a nine-day ActBlue feed stall went unnoticed
     in Aug 2026 while this page kept publishing a confident number. */
  .freshness.stale {{ color: var(--priority-medium); }}
  .freshness.dead {{ color: var(--priority-high); font-weight: 600; }}

  .label {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--text-tertiary);
  }}

  .stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 12px; margin-bottom: 28px;
  }}
  .stat {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 3px; padding: 14px 16px;
  }}
  .stat-value {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 26px; line-height: 1.1; margin-top: 6px;
  }}
  .delta {{
    display: inline-block; margin-top: 7px;
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 11px; letter-spacing: 0.02em;
  }}
  .delta.up {{ color: var(--priority-low); }}
  .delta.down {{ color: var(--priority-high); }}
  .delta.flat, .delta.none {{ color: var(--text-tertiary); }}

  .card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 3px; padding: 20px; margin-bottom: 16px;
  }}
  .card-title {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--text-tertiary); margin-bottom: 16px;
  }}

  /* --- timeline ---------------------------------------------------------- */
  .tl-head {{ display: flex; align-items: baseline; justify-content: space-between;
              gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }}
  .tl-legend {{ display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--text-secondary); }}
  .tl-key {{ display: inline-flex; align-items: center; gap: 6px; }}
  .tl-swatch {{ width: 14px; height: 2px; border-radius: 1px; display: inline-block; }}
  .tl-chart {{ position: relative; }}
  .tl-chart svg {{ display: block; width: 100%; height: auto; overflow: visible; }}
  .tl-grid {{ stroke: var(--border-light); stroke-width: 1; }}
  .tl-base {{ stroke: var(--border); stroke-width: 1; }}
  .tl-tick {{ fill: var(--text-tertiary); font-size: 10px;
              font-family: "IBM Plex Mono", ui-monospace, monospace; font-variant-numeric: tabular-nums; }}
  .tl-end {{ fill: var(--text); font-size: 12px; font-weight: 600; }}
  .tl-line {{ fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }}
  .tl-dot {{ stroke: var(--surface); stroke-width: 2; }}
  .tl-cross {{ stroke: var(--text-tertiary); stroke-width: 1; }}
  .tl-col {{ fill: var(--series-total); }}
  .tl-col.partial {{ fill-opacity: .4; }}
  .tl-col:hover, .tl-col.on {{ opacity: .78; }}
  .tl-tip {{
    position: absolute; pointer-events: none; z-index: 2; white-space: nowrap;
    background: var(--surface); border: 1px solid var(--border); border-radius: 3px;
    padding: 7px 9px; font-size: 12px; color: var(--text); line-height: 1.5;
    box-shadow: 0 2px 8px rgba(0,0,0,.08);
  }}
  .tl-tip[hidden] {{ display: none; }}
  .tl-tip .k {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
  .tl-tip .d {{ color: var(--text-secondary); font-size: 11px; }}
  .tl-sub {{ margin: 22px 0 8px; font-size: 12px; color: var(--text-secondary); }}
  .tl-note {{ margin-top: 10px; font-size: 12px; color: var(--text-tertiary); }}
  /* The chart is one viewBox scaled to fit, so its text shrinks with it: at
     phone width 10-unit ticks render near 4px. SVG type is in viewBox units,
     so it is enlarged here to land back at a readable size on screen. */
  @media (max-width: 560px) {{
    .tl-tick {{ font-size: 19px; }}
    .tl-end {{ font-size: 21px; }}
    /* The weekly chart is too short at this width for four labels; the
       gridlines stay, and the floor and ceiling carry the scale. */
    .tl-tick.tl-mid {{ display: none; }}
  }}
  .tl-table {{ margin-top: 12px; font-size: 12px; }}
  .tl-table summary {{ cursor: pointer; color: var(--text-secondary); }}
  .tl-table table {{ border-collapse: collapse; margin-top: 8px; width: 100%;
                     font-variant-numeric: tabular-nums; }}
  .tl-table th, .tl-table td {{ text-align: right; padding: 4px 8px; border-bottom: 1px solid var(--border-light); }}
  .tl-table th:first-child, .tl-table td:first-child {{ text-align: left; }}
  .tl-table th {{ color: var(--text-tertiary); font-weight: 500; }}

  .headline {{
    display: flex; align-items: baseline; gap: 10px;
    flex-wrap: wrap; margin-bottom: 4px;
  }}
  .headline-value {{
    font-family: Georgia, 'Times New Roman', serif; font-size: 34px; line-height: 1.05;
  }}
  .headline-note {{ font-size: 13px; color: var(--text-secondary); }}

  /* Two stat tiles: a countdown and a share. Both are single values, so
     they are numbers rather than plots — a 2-slice pie or a one-bar chart
     would encode less than the figure itself. */
  .alert {{
    background: var(--priority-medium-bg);
    border: 1px solid var(--priority-medium);
    border-radius: 3px; padding: 10px 14px; margin-top: 16px;
    font-size: 12px; line-height: 1.6; color: var(--text);
  }}
  .alert b {{ font-weight: 600; }}

  .figures {{
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 12px; margin-top: 20px;
  }}
  .figure {{
    background: var(--ground); border: 1px solid var(--border-light);
    border-radius: 3px; padding: 14px 16px;
  }}
  .figure-value {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 32px; line-height: 1.05;
  }}
  .figure-label {{ font-size: 13px; margin-top: 6px; }}
  .figures.three {{ grid-template-columns: 1fr 1fr 1fr; margin-top: 4px; }}
  .pace-status {{
    margin-top: 14px; padding: 10px 14px; border-radius: 3px;
    font-size: 13px; line-height: 1.5; border: 1px solid var(--border);
  }}
  .pace-status b {{ font-weight: 600; }}
  .pace-icon {{ margin-right: 6px; font-weight: 700; }}
  .pace-status.good .pace-icon, .pace-status.good b {{ color: var(--priority-low); }}
  .pace-status.good {{ border-color: var(--priority-low); }}
  .pace-status.behind .pace-icon, .pace-status.behind b {{ color: var(--priority-high); }}
  .pace-status.behind {{ border-color: var(--priority-high); }}
  .figure-note {{
    font-size: 12px; color: var(--text-secondary);
    margin-top: 4px; line-height: 1.5;
  }}

  .meter {{ margin-top: 18px; }}
  .meter + .meter {{ margin-top: 20px; }}
  .meter-head {{
    display: flex; justify-content: space-between;
    align-items: baseline; margin-bottom: 7px; gap: 12px;
  }}
  .meter-pct {{
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 15px; color: var(--accent);
  }}
  .meter-track {{
    height: 8px; background: var(--border-light);
    border-radius: 4px; overflow: hidden;
  }}
  .meter-fill {{ height: 100%; background: var(--accent); border-radius: 4px; }}
  .meter-foot {{
    display: flex; justify-content: space-between;
    margin-top: 6px; font-size: 12px; color: var(--text-secondary); gap: 12px;
  }}
  .meter-foot b {{ color: var(--text); font-weight: 500; }}

  @media (max-width: 600px) {{
    .stats {{ grid-template-columns: 1fr 1fr; }}
    .headline-value {{ font-size: 28px; }}
    /* Stack rather than squeeze into two narrow columns */
    .meter-foot {{ flex-direction: column; gap: 2px; }}
    .figures, .figures.three {{ grid-template-columns: 1fr; }}
  }}
{AUTH_CSS}</style>
</head>
<body>
<nav class="site-nav" id="siteNav">
  <a href="../index.html">Tasks</a>
  <a href="../questionnaires/index.html">Questionnaires</a>
  <a href="index.html" class="active">Fundraising</a>
  <a href="../calendar/index.html">Calendar</a>
  <a href="../calltime/index.html">Call Time</a>
</nav>
{AUTH_HTML}

<div class="app" id="appRoot" style="display:none">

  <h1 class="page-title">Fundraising</h1>
  <p class="page-sub">Updated {updated}{freshness}</p>

  <div class="stats">
    <div class="stat">
      <div class="label">Total raised</div>
      <div class="stat-value">{money(total)}</div>
      {delta_html(total, week_total)}
    </div>
    <div class="stat">
      <div class="label">Donors</div>
      <div class="stat-value">{donors:,}</div>
      {delta_html(donors, week_donors, as_money=False)}
    </div>
    <div class="stat">
      <div class="label">Average gift</div>
      <div class="stat-value">{money(avg, cents=True)}</div>
      <span class="delta none">{count:,} donations</span>
    </div>
    <div class="stat">
      <div class="label">Projected total</div>
      <div class="stat-value">{money(projected)}</div>
      <span class="delta none">incl. {money(match)} match</span>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Public financing &mdash; {ratio:g}:1 Berkeley match</div>

    <div class="headline">
      <span class="headline-value">{money(projected)}</span>
      <span class="headline-note">projected total &mdash; {money(total)} raised plus {money(match)} in matching funds</span>
    </div>
{cert_banner}
    <div class="meter">
      <div class="meter-head">
        <span class="label">{match_label}</span>
        <span class="meter-pct">{match_pct:.0f}%</span>
      </div>
      <div class="meter-track"><div class="meter-fill" style="width:{match_pct:.1f}%"></div></div>
      <div class="meter-foot">
        <span>{money(match)} {match_word}</span>
        <span>{money(match_left)} still available of the {money(match_cap)} cap</span>
      </div>
    </div>

    <div class="figures">
      <div class="figure">
        <div class="figure-value">{countdown_value}</div>
        <div class="figure-label">{countdown_label}</div>
        <div class="figure-note">{countdown_note}</div>
      </div>
      <div class="figure">
        <div class="figure-value">{donor_share:.0f}%</div>
        <div class="figure-label">of donors are Berkeley residents</div>
        <div class="figure-note">{bky_donors:,} of {donors:,} &middot; they give {bky_share:.0f}% of all money raised</div>
      </div>
    </div>
  </div>
{pace}
{timeline}

</div>
{AUTH_JS}
</body>
</html>'''

    with open(out_path, 'w') as f:
        f.write(page)
    print(f"Generated {out_path}")


if __name__ == '__main__':
    generate(sys.argv[1], sys.argv[2])
