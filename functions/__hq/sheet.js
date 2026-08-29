// Edge proxy between the call time page and the Google Sheet.
//
// The page fetches /__hq/sheet on its own origin; this adds the shared token and
// forwards to the Apps Script web app. The token never reaches the browser, so
// nobody with devtools open walks away with read/write on a sheet full of
// contact PII.
//
// Reaching this at all requires the hq_pass cookie: _middleware.js runs first on
// every request and only calls next() once the passcode cookie verifies.
//
// Set in Cloudflare Pages -> Settings -> Environment variables, both as secrets:
//   SHEET_WEBAPP_URL   the /exec URL from Deploy > New deployment
//   SHEET_TOKEN        the same string as the sheet's SHEET_TOKEN script property

const JSON_HEADERS = {
  'Content-Type': 'application/json',
  // Contact data. Never let an intermediary or the back-forward cache hold it.
  'Cache-Control': 'no-store, private',
};

function fail(status, error, code) {
  return new Response(JSON.stringify({ ok: false, error, code: code || 'error' }),
    { status, headers: JSON_HEADERS });
}

export async function onRequest(context) {
  const { request, env } = context;

  const url = env.SHEET_WEBAPP_URL;
  const token = env.SHEET_TOKEN;
  // Fail closed and say which half is missing — a silent empty list would read
  // as "the sheet is empty" and invite someone to retype 141 contacts.
  if (!url || !token) {
    return fail(503, 'Sheet bridge is not configured: ' +
      (!url ? 'SHEET_WEBAPP_URL' : 'SHEET_TOKEN') + ' is unset in Cloudflare.',
      'unconfigured');
  }

  let body;
  if (request.method === 'GET') {
    body = { action: 'read' };
  } else if (request.method === 'POST') {
    try {
      body = await request.json();
    } catch (e) {
      return fail(400, 'Malformed request body.', 'badrequest');
    }
  } else {
    return fail(405, 'Method not allowed.', 'badmethod');
  }

  // The token is added here, never accepted from the caller: a page that could
  // supply its own would make the same request from anywhere.
  delete body.token;
  const payload = JSON.stringify({ ...body, token });

  let res;
  try {
    res = await fetch(url, {
      method: 'POST',
      // Apps Script answers /exec with a 302 to googleusercontent.com; the
      // default redirect: 'follow' is what actually returns the JSON.
      redirect: 'follow',
      headers: { 'Content-Type': 'application/json' },
      body: payload,
    });
  } catch (e) {
    return fail(502, 'Could not reach the sheet: ' + e.message, 'unreachable');
  }

  const text = await res.text();
  if (!res.ok) {
    return fail(502, 'Sheet returned HTTP ' + res.status, 'upstream');
  }
  // Apps Script serves its sign-in page as HTML when a deployment is set to
  // anything narrower than "Anyone", which would otherwise surface as a JSON
  // parse error with no hint at the cause.
  if (text.trim().startsWith('<')) {
    return fail(502, 'The Apps Script deployment is not public. Redeploy it with ' +
      'Access set to "Anyone".', 'notpublic');
  }

  return new Response(text, { status: 200, headers: JSON_HEADERS });
}
