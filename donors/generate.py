"""Generate the static fundraising dashboard from aggregated donor data.

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
    min-height: 100vh; display: flex;
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


def generate(data_path, out_path):
    with open(data_path) as f:
        d = json.load(f)

    total     = d['total_raised']
    donors    = d['unique_donors']
    count     = d['donation_count']
    avg       = d['average_donation']
    updated   = str(d.get('updated', ''))[:10]

    bky_raised = d.get('berkeley_raised', 0)
    bky_count  = d.get('berkeley_donations', 0)
    qualifying = d.get('qualifying', 0)
    match      = d.get('match_earned', 0)
    match_left = d.get('match_remaining', 0)
    match_cap  = d.get('match_cap', 52000)
    ratio      = d.get('match_ratio', 6)
    projected  = d.get('projected_total', total + match)

    week_total  = d.get('week_ago_total', '')
    week_donors = d.get('week_ago_donors', '')

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

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    --priority-low: #6B956B;
    --team-bg: #F2F2EE;
    --hover: #F4F4F0;
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
      --priority-low: #7DAF7D;
      --team-bg: #222226;
      --hover: #24242A;
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
    .figures {{ grid-template-columns: 1fr; }}
  }}
{AUTH_CSS}</style>
</head>
<body>
{AUTH_HTML}
<nav class="site-nav" id="siteNav" style="display:none">
  <a href="../index.html">Tasks</a>
  <a href="../questionnaires/index.html">Questionnaires</a>
  <a href="index.html" class="active">Fundraising</a>
</nav>

<div class="app" id="appRoot" style="display:none">

  <h1 class="page-title">Fundraising</h1>
  <p class="page-sub">Updated {updated}</p>

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
    <div class="card-title">Public financing &mdash; {ratio}:1 Berkeley match</div>

    <div class="headline">
      <span class="headline-value">{money(projected)}</span>
      <span class="headline-note">projected total &mdash; {money(total)} raised plus {money(match)} in matching funds</span>
    </div>

    <div class="meter">
      <div class="meter-head">
        <span class="label">Matching funds earned</span>
        <span class="meter-pct">{match_pct:.0f}%</span>
      </div>
      <div class="meter-track"><div class="meter-fill" style="width:{match_pct:.1f}%"></div></div>
      <div class="meter-foot">
        <span>{money(match)} earned</span>
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

</div>
{AUTH_JS}
</body>
</html>'''

    with open(out_path, 'w') as f:
        f.write(page)
    print(f"Generated {out_path}")


if __name__ == '__main__':
    generate(sys.argv[1], sys.argv[2])
