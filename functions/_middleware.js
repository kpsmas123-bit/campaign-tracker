// Site-wide passcode gate for Cloudflare Pages.
//
// Runs at the edge on EVERY request, so it covers the .sql, .json and .py files
// in this repo as well as the HTML. The in-app passphrase only hides the UI —
// it is client-side JavaScript and cannot stop anyone fetching a data file
// directly. This can.
//
// Set SITE_PASSCODE (and optionally COOKIE_SECRET) in
// Cloudflare Pages -> Settings -> Environment variables. Mark both as secrets.
//
// This is a shared code, deliberately: one passcode for the whole team rather
// than per-person accounts. It is NOT a substitute for Supabase RLS, which is
// what actually protects the data itself.

const COOKIE = 'hq_pass';
const MAX_AGE = 60 * 60 * 24 * 30; // 30 days

const enc = new TextEncoder();

async function sign(value, secret) {
  const key = await crypto.subtle.importKey(
    'raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(value));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, '0')).join('');
}

// Constant-time compare: a plain === on a secret leaks length and prefix
// through timing, and this runs on every request.
function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function getCookie(req, name) {
  const raw = req.headers.get('Cookie') || '';
  for (const part of raw.split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k === name) return v.join('=');
  }
  return null;
}

function page(error) {
  return `<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campaign HQ</title>
<style>
  :root { color-scheme: light dark; }
  body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:#FBFBF9; color:#1A1A18;
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }
  @media (prefers-color-scheme: dark) { body { background:#151516; color:#EDEDEA; } }
  form { width:100%; max-width:300px; padding:0 24px; }
  h1 { font-family:Georgia,'Times New Roman',serif; font-weight:normal; font-size:22px; margin:0 0 4px; }
  p  { font-size:13px; color:#6E6E6C; margin:0 0 18px; }
  input { width:100%; box-sizing:border-box; padding:9px 11px; font-size:14px;
          border:1px solid #E6E6E2; border-radius:4px; background:transparent; color:inherit; }
  input:focus { outline:none; border-color:#4A6FA5; }
  button { width:100%; margin-top:9px; padding:9px 11px; font-size:13px; cursor:pointer;
           border:1px solid #4A6FA5; border-radius:4px; background:#4A6FA5; color:#fff; }
  .err { color:#C45240; font-size:12px; margin-top:9px; }
</style>
<form method="POST">
  <h1>Campaign HQ</h1>
  <p>Enter the site passcode.</p>
  <input type="password" name="passcode" autocomplete="current-password" autofocus>
  <button type="submit">Continue</button>
  ${error ? '<div class="err">' + error + '</div>' : ''}
</form>`;
}

export async function onRequest(context) {
  const { request, env, next } = context;
  const passcode = env.SITE_PASSCODE;

  // Fail closed. A missing passcode must not silently publish the whole site.
  if (!passcode) {
    return new Response('SITE_PASSCODE is not configured.', {
      status: 503, headers: { 'Content-Type': 'text/plain' },
    });
  }
  const secret = env.COOKIE_SECRET || passcode;
  const expected = await sign('ok', secret);

  const cookie = getCookie(request, COOKIE);
  if (cookie && safeEqual(cookie, expected)) return next();

  if (request.method === 'POST') {
    const form = await request.formData();
    if (safeEqual(String(form.get('passcode') || ''), passcode)) {
      return new Response(null, {
        status: 303,
        headers: {
          'Location': new URL(request.url).pathname,
          'Set-Cookie': `${COOKIE}=${expected}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${MAX_AGE}`,
        },
      });
    }
    return new Response(page('Incorrect passcode.'), {
      status: 401,
      headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' },
    });
  }

  return new Response(page(''), {
    status: 401,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' },
  });
}
