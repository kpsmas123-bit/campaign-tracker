# Hosting: Cloudflare Pages + site passcode

The site moved off GitHub Pages so the repository could be made **private**.

## What each layer actually protects

| Layer | Protects | Does not protect |
| --- | --- | --- |
| Private repo | Git history — past commits, removed files, research | Anything the site serves |
| `functions/_middleware.js` | Every URL on the site, including `.sql`, `.json`, `.py` | The Supabase data itself |
| Supabase RLS | The data, against anyone holding the publishable key | — |

The in-app passphrase is client-side JavaScript. It hides the interface; it has
never stopped anyone fetching a data file directly. The edge gate is what does.

## One-time setup

1. **Cloudflare Pages → Create project → Connect to Git**, pick this repo.
   Framework preset **None**, no build command, output directory `/`.
2. **Settings → Environment variables**, add as *secrets*:
   - `SITE_PASSCODE` — the shared code the team types once per browser.
   - `COOKIE_SECRET` — optional, any long random string. Defaults to
     `SITE_PASSCODE`; setting it separately means rotating one does not
     invalidate the other.
3. Deploy, and check the `*.pages.dev` URL shows the passcode screen.
4. **Squarespace DNS** (nameservers are `nsd1–4.squarespacedns.com`): point the
   `hq` CNAME at the `*.pages.dev` target instead of `kpsmas123-bit.github.io`.
5. Once `hq.dariaforberkeley.com` serves from Cloudflare, make the repo private,
   disable GitHub Pages, and delete `CNAME` (a Pages artifact, unused here).

Do it in that order. Flipping the repo private before Cloudflare is serving
takes the site down.

## Notes

- The gate **fails closed**: with no `SITE_PASSCODE` set it returns 503 rather
  than publishing the site.
- The cookie is HMAC-signed, `HttpOnly`, `Secure`, and lasts 30 days.
- Changing `SITE_PASSCODE` signs everyone out at the next request.
- Private repos bill Actions minutes rounded up per run. The hourly calendar
  sync is ~720 runs/month against a 2,000-minute free allowance; dropping it to
  every three hours cuts that to ~240.
