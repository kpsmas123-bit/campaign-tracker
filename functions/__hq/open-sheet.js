// "Open sheet" on the call time page lands here and is redirected to the
// spreadsheet itself.
//
// The address lives in Cloudflare rather than in the page because this repo is
// public: a sheet ID committed here would be readable by anyone, where this
// route sits behind the passcode gate like everything else (_middleware.js).
// Opening the link still needs a Google account with access to the sheet.
//
// Set in Cloudflare Pages -> Settings -> Environment variables:
//   SHEET_EDIT_URL   the spreadsheet's https://docs.google.com/spreadsheets/d/.../edit URL

export async function onRequest({ env }) {
  const url = env.SHEET_EDIT_URL;
  if (!url || !/^https:\/\/docs\.google\.com\/spreadsheets\//.test(url)) {
    return new Response(
      'The sheet link is not configured: set SHEET_EDIT_URL in Cloudflare Pages ' +
      'to the spreadsheet\'s docs.google.com URL, then redeploy.',
      { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' } });
  }
  return new Response(null, { status: 302, headers: { Location: url, 'Cache-Control': 'no-store' } });
}
