# Donor Dashboard Setup

> **The generated dashboard is public.** `donors/index.html` is a static file
> served by GitHub Pages with the numbers baked in — unlike Tasks and
> Questionnaires, there is no auth gate on it. It contains aggregates only
> (no names, addresses, or emails), but anyone with the URL can read the
> fundraising totals. The `Raw` tab stays private in the Google Sheet and is
> never published.

## Berkeley matching rules encoded here

Verified against the City of Berkeley Public Financing Program Guide and the
2026 disbursement tracker (updated 7/23/2026):

| Rule | Value |
|---|---|
| Match ratio | 6:1 |
| Max matchable per contribution | $60 |
| Who qualifies | Berkeley residents only |
| City Council matching cap | $52,000 |
| Qualifying contributions to max the cap | $8,666.67 |

Non-Berkeley contributions still count toward money raised but earn no match.
If any of these change, update the constants at the top of `apps-script.js`.

## 1. Create the Master Google Sheet

1. Create a new Google Sheet (e.g. "Donor Tracker Master")
2. Tabs are created automatically on first run: **Raw**, **Daily**, **Summary**, **History**
3. Open Extensions > Apps Script
4. Paste the contents of `apps-script.js` (in this folder)
5. Save the script

## 2. Configure the Apps Script

In `apps-script.js`, check two settings:

- `FOLDER_NAME` — the Drive folder to collect reports in. The script creates it
  on first run if it doesn't exist, so there is no folder ID to look up.
- `REPORT_PREFIX` — your ActBlue report template name. ActBlue names reports
  `TemplateName_Frequency_Date` (e.g. `report1.1_Daily_August5`), so this must
  match the template name exactly.

ActBlue always deposits reports into your Drive root — there is no way to point it
at a folder. On each run the script moves any report matching `REPORT_PREFIX` out of
the root and into `FOLDER_NAME` before consolidating.

## 3. Set up the Apps Script trigger

1. In Apps Script, click the clock icon (Triggers) in the left sidebar
2. Click "Add Trigger"
3. Function: `consolidate`, Event source: Time-driven, Day timer, 6am–7am
4. Save

## 4. Publish the Dashboard tabs as CSV

1. In the master sheet, go to File > Share > Publish to web
2. Under "Link", select the **Daily** tab and **CSV** format — copy that URL
3. Repeat for the **Summary** tab — copy that URL
4. Update the GitHub Action (`donor-dashboard.yml`) with both URLs

## 4b. Week-over-week change

The ActBlue export has no date column, so the script writes one snapshot row per
day to the **History** tab and derives the weekly change from it. The dashboard
shows "no prior week" until there are snapshots at least 7 days apart — that is
expected on the first runs, not a bug.

## 5. Run manually first

In Apps Script, select `consolidate` from the function dropdown and click Run.
Grant the permissions it asks for (Drive + Sheets access). Verify the Raw/Daily/Summary
tabs populate correctly.

## 6. Enable the GitHub Action

The action runs daily at 9am UTC (2am PT). You can also trigger it manually
from the Actions tab on GitHub. On first run, verify the dashboard appears at:
`https://kpsmas123-bit.github.io/campaign-tracker/donors/`
