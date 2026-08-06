/**
 * ActBlue Donor Consolidator
 *
 * Sweeps ActBlue scheduled reports out of Drive root into a folder, reads
 * every report, deduplicates by Lineitem ID, and writes four tabs:
 *
 *   - Raw     every donation, including names — KEEP PRIVATE, never publish
 *   - Summary metric/value totals + Berkeley match math — read by the site
 *   - History one snapshot row per day, for week-over-week change
 *   - Daily   city/occupation/amount breakdowns, for reference in the sheet
 *
 * Only the Summary tab feeds the dashboard, and it holds aggregates only —
 * no names, addresses, emails, or phone numbers. Do not publish Raw.
 */

// ── CONFIG ──────────────────────────────────────────────────────────
var FOLDER_NAME = 'ActBlue Reports';        // Drive folder to collect reports in

// Substring common to every ActBlue report filename, matched case-insensitively
// anywhere in the name. It must stay loose enough to cover BOTH report types:
//   one-off custom : daria-wrubel-233102-custom-report-report1.1-2026-07-01-2026-07-28
//   scheduled daily: Report1.1_Daily_08/06/2026
// This was previously 'custom-report-report1.1', which only matched the first
// form. When the campaign switched to scheduled daily reports every new file
// was silently skipped, so the sheet stayed frozen on the 7/28 custom report
// while the script kept running and reporting success.
var REPORT_MATCH = 'report1.1';

// Berkeley Fair Elections Act public financing (verified against the City's
// 2026 Public Financing Program Guide and the 7/23/2026 disbursement tracker):
//   - 6:1 match on qualifying contributions of up to $60
//   - Only contributions from Berkeley residents qualify
//   - City Council cap is $52,000 in total matching funds
var MATCH_RATIO   = 6;         // $6 public funds per $1 qualifying contribution
var MATCH_MAX_PER = 60;        // $60 is the per-DONOR contribution limit, not per gift
var MATCH_CAP     = 52000;     // Max total matching funds, City Council
var MATCH_CITY    = 'berkeley';// Residency test against Donor City

// To be certified into the program a candidate must first collect at least 30
// Qualified Contributions from at least 30 unique contributors, each $10–$60,
// totalling at least $580. No matching funds are paid until that is met.
var QUALIFY_MIN_COUNT  = 30;
var QUALIFY_MIN_GIFT   = 10;
var QUALIFY_MIN_TOTAL  = 580;
// ────────────────────────────────────────────────────────────────────

// Qualifying contributions needed to max out the match: $52,000 / 6 = $8,666.67
var GOAL_DIRECT = MATCH_CAP / MATCH_RATIO;
var GOAL_TOTAL  = GOAL_DIRECT + MATCH_CAP;

/**
 * Find the reports folder by name, creating it if it doesn't exist.
 */
function getReportsFolder() {
  var folders = DriveApp.getFoldersByName(FOLDER_NAME);
  return folders.hasNext() ? folders.next() : DriveApp.createFolder(FOLDER_NAME);
}

function isReport(name) {
  return name.toLowerCase().indexOf(REPORT_MATCH.toLowerCase()) !== -1;
}

/**
 * Collect ActBlue reports from anywhere in Drive into the reports folder.
 * REPORT_MATCH is matched anywhere in the filename, not just at the start,
 * because the two report types are named quite differently. Run before
 * consolidate() — consolidate() calls it for you.
 */
function moveReportsToFolder() {
  var folder = getReportsFolder();
  var folderId = folder.getId();
  var moved = 0, alreadyThere = 0;

  // Searches all of Drive, not just the root. The previous version scanned
  // DriveApp.getRootFolder() only, so a report delivered into any subfolder was
  // never collected and never reported as missing.
  var files = DriveApp.searchFiles(
    "title contains '" + REPORT_MATCH.replace(/'/g, "\\'") + "' and trashed = false");

  while (files.hasNext()) {
    var file = files.next();
    if (!isReport(file.getName())) continue;

    var mime = file.getMimeType();
    if (mime !== MimeType.GOOGLE_SHEETS && mime !== MimeType.CSV) continue;

    // Already collected — moving it onto itself would churn revisions.
    var parents = file.getParents(), inFolder = false;
    while (parents.hasNext()) {
      if (parents.next().getId() === folderId) { inFolder = true; break; }
    }
    if (inFolder) { alreadyThere++; continue; }

    file.moveTo(folder);
    moved++;
    Logger.log('Moved: ' + file.getName());
  }

  Logger.log('Moved ' + moved + ' report(s) into "' + FOLDER_NAME + '" (' +
             alreadyThere + ' already there)');
  if (moved === 0 && alreadyThere === 0) {
    Logger.log('WARNING: no files anywhere in Drive match "' + REPORT_MATCH +
               '". Nothing will update until a report lands.');
  }
}

function consolidate() {
  moveReportsToFolder();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ssId = ss.getId();   // re-opened after the read loops; see below

  // Collect all rows from every sheet in the folder
  var folder = getReportsFolder();
  var files = folder.getFilesByType(MimeType.GOOGLE_SHEETS);
  var seen = {};   // Lineitem ID -> row
  var rows = [];

  // Freshness tracking. Without this the sheet reports a confident number with
  // no indication of how old the underlying reports are, which is exactly how
  // the 7/28 stall went unnoticed for nine days.
  var newestName = '', newestTime = 0, filesRead = 0;
  function noteFile(f) {
    filesRead++;
    var t = f.getLastUpdated().getTime();
    if (t > newestTime) { newestTime = t; newestName = f.getName(); }
  }

  while (files.hasNext()) {
    var file = files.next();
    try {
      var sheet = SpreadsheetApp.openById(file.getId()).getSheets()[0];
      var data = sheet.getDataRange().getValues();
      var header = data[0];

      // Find column indices
      var colId     = indexOf(header, 'Lineitem ID');
      var colAmount = indexOf(header, 'Amount');
      var colFirst  = indexOf(header, 'Donor First Name');
      var colLast   = indexOf(header, 'Donor Last Name');
      var colCity   = indexOf(header, 'Donor City');
      var colOcc    = indexOf(header, 'Donor Occupation');

      if (colId < 0 || colAmount < 0) {
        Logger.log('Skipping "' + file.getName() + '" — no Lineitem ID/Amount columns');
        continue; // not an ActBlue report
      }
      Logger.log('Reading "' + file.getName() + '" (' + (data.length - 1) + ' rows)');
      noteFile(file);

      for (var i = 1; i < data.length; i++) {
        var id = String(data[i][colId]).trim();
        if (!id || seen[id]) continue;
        seen[id] = true;
        rows.push({
          id: id,
          amount: parseFloat(data[i][colAmount]) || 0,
          first: colFirst >= 0 ? String(data[i][colFirst]).trim() : '',
          last: colLast >= 0 ? String(data[i][colLast]).trim() : '',
          city: colCity >= 0 ? String(data[i][colCity]).trim() : '',
          occupation: colOcc >= 0 ? String(data[i][colOcc]).trim() : '',
        });
      }
    } catch (e) {
      Logger.log('Skipping file ' + file.getName() + ': ' + e.message);
    }
  }

  // Also read CSV files (ActBlue sometimes deposits plain CSVs)
  var csvFiles = folder.getFilesByType(MimeType.CSV);
  while (csvFiles.hasNext()) {
    var csvFile = csvFiles.next();
    try {
      var content = csvFile.getBlob().getDataAsString();
      var parsed = Utilities.parseCsv(content);
      var header = parsed[0];
      var colId     = indexOf(header, 'Lineitem ID');
      var colAmount = indexOf(header, 'Amount');
      var colFirst  = indexOf(header, 'Donor First Name');
      var colLast   = indexOf(header, 'Donor Last Name');
      var colCity   = indexOf(header, 'Donor City');
      var colOcc    = indexOf(header, 'Donor Occupation');

      if (colId < 0 || colAmount < 0) continue;
      noteFile(csvFile);

      for (var i = 1; i < parsed.length; i++) {
        var id = String(parsed[i][colId]).trim();
        if (!id || seen[id]) continue;
        seen[id] = true;
        rows.push({
          id: id,
          amount: parseFloat(parsed[i][colAmount]) || 0,
          first: colFirst >= 0 ? String(parsed[i][colFirst]).trim() : '',
          last: colLast >= 0 ? String(parsed[i][colLast]).trim() : '',
          city: colCity >= 0 ? String(parsed[i][colCity]).trim() : '',
          occupation: colOcc >= 0 ? String(parsed[i][colOcc]).trim() : '',
        });
      }
    } catch (e) {
      Logger.log('Skipping CSV ' + csvFile.getName() + ': ' + e.message);
    }
  }

  // Re-acquire the Master before writing. The loops above call
  // SpreadsheetApp.openById() once per report file, which moves SpreadsheetApp's
  // internal "active sheet" pointer into the last report opened. insertSheet()
  // positions relative to that pointer, so writing through the stale handle
  // fails with "Sheet <id> not found" — where the id belongs to a report tab,
  // not to this spreadsheet.
  SpreadsheetApp.flush();
  ss = SpreadsheetApp.openById(ssId);
  ss.setActiveSheet(ss.getSheets()[0]);

  // ── Write Raw tab (private, not published) ──
  var rawSheet = getOrCreateSheet(ss, 'Raw');
  rawSheet.clear();
  rawSheet.appendRow(['Lineitem ID', 'Amount', 'First', 'Last', 'City', 'Occupation']);
  rows.forEach(function(r) {
    rawSheet.appendRow([r.id, r.amount, r.first, r.last, r.city, r.occupation]);
  });

  // ── Aggregate by date (Lineitem ID encodes timestamp) ──
  // ActBlue Lineitem IDs are sequential, so we group by the file's date range.
  // Since we don't have per-donation dates in this export, we aggregate by city and totals.

  // ── City breakdown ──
  var byCityMap = {};
  rows.forEach(function(r) {
    var city = r.city || 'Unknown';
    if (!byCityMap[city]) byCityMap[city] = { count: 0, amount: 0 };
    byCityMap[city].count++;
    byCityMap[city].amount += r.amount;
  });
  var cities = Object.keys(byCityMap).sort(function(a, b) {
    return byCityMap[b].amount - byCityMap[a].amount;
  });

  // ── Occupation breakdown ──
  var byOccMap = {};
  rows.forEach(function(r) {
    var occ = r.occupation || 'Unknown';
    if (!byOccMap[occ]) byOccMap[occ] = { count: 0, amount: 0 };
    byOccMap[occ].count++;
    byOccMap[occ].amount += r.amount;
  });
  var occs = Object.keys(byOccMap).sort(function(a, b) {
    return byOccMap[b].amount - byOccMap[a].amount;
  });

  // ── Amount distribution ──
  var byAmountMap = {};
  rows.forEach(function(r) {
    var bucket = String(Math.round(r.amount));
    if (!byAmountMap[bucket]) byAmountMap[bucket] = 0;
    byAmountMap[bucket]++;
  });

  // ── Write Daily tab (published as CSV) ──
  // Format: section headers followed by data rows
  var dailySheet = getOrCreateSheet(ss, 'Daily');
  dailySheet.clear();

  // City breakdown
  dailySheet.appendRow(['[cities]']);
  dailySheet.appendRow(['city', 'donors', 'amount']);
  cities.forEach(function(c) {
    dailySheet.appendRow([c, byCityMap[c].count, byCityMap[c].amount]);
  });

  // Occupation breakdown
  dailySheet.appendRow(['[occupations]']);
  dailySheet.appendRow(['occupation', 'donors', 'amount']);
  occs.forEach(function(o) {
    dailySheet.appendRow([o, byOccMap[o].count, byOccMap[o].amount]);
  });

  // Amount distribution
  dailySheet.appendRow(['[amounts]']);
  dailySheet.appendRow(['amount', 'count']);
  Object.keys(byAmountMap).sort(function(a,b){ return parseFloat(a)-parseFloat(b); }).forEach(function(a) {
    dailySheet.appendRow([a, byAmountMap[a]]);
  });

  // ── Totals ──
  var totalRaised = rows.reduce(function(s, r) { return s + r.amount; }, 0);
  var uniqueDonors = {};
  rows.forEach(function(r) {
    var key = (r.first + ' ' + r.last).toLowerCase().trim();
    if (key) uniqueDonors[key] = true;
  });
  var donorCount = Object.keys(uniqueDonors).length;
  var avgDonation = rows.length > 0 ? totalRaised / rows.length : 0;

  // ── Berkeley matching-funds math ──
  // Only Berkeley residents qualify, and only the first $60 of each
  // contribution is matchable.
  var berkeleyRows = rows.filter(function(r) {
    return r.city.toLowerCase().trim() === MATCH_CITY;
  });
  var berkeleyRaised = berkeleyRows.reduce(function(s, r) { return s + r.amount; }, 0);

  // Total each Berkeley donor's giving, then cap at $60 PER DONOR. The $60
  // limit is a per-donor total, not a per-gift ceiling, so a donor who gives
  // twice adds nothing matchable beyond their first $60.
  var berkeleyByDonor = {};
  berkeleyRows.forEach(function(r) {
    var key = (r.first + ' ' + r.last).toLowerCase().trim() || r.id;
    berkeleyByDonor[key] = (berkeleyByDonor[key] || 0) + r.amount;
  });
  var berkeleyDonors = Object.keys(berkeleyByDonor).length;
  var qualifying = Object.keys(berkeleyByDonor).reduce(function(s, k) {
    return s + Math.min(berkeleyByDonor[k], MATCH_MAX_PER);
  }, 0);

  // ── Certification threshold ──
  // Counted per contributor: each needs at least one gift in the $10–$60 band.
  var qualifiedContributors = Object.keys(berkeleyByDonor).filter(function(k) {
    return berkeleyByDonor[k] >= QUALIFY_MIN_GIFT;
  });
  var qualifiedCount = qualifiedContributors.length;
  var qualifiedTotal = qualifiedContributors.reduce(function(s, k) {
    return s + Math.min(berkeleyByDonor[k], MATCH_MAX_PER);
  }, 0);
  var isCertified = qualifiedCount >= QUALIFY_MIN_COUNT &&
                    qualifiedTotal >= QUALIFY_MIN_TOTAL;
  var certifyShort = Math.max(0, QUALIFY_MIN_COUNT - qualifiedCount);

  var matchEarned    = Math.min(qualifying * MATCH_RATIO, MATCH_CAP);
  var matchRemaining = MATCH_CAP - matchEarned;
  var projectedTotal = totalRaised + matchEarned;

  // ── History tab: one snapshot row per day, for week-over-week ──
  var tz = ss.getSpreadsheetTimeZone() || 'America/Los_Angeles';
  var today = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');

  var historySheet = getOrCreateSheet(ss, 'History');
  if (historySheet.getLastRow() === 0) {
    historySheet.appendRow(['date', 'total_raised', 'donation_count', 'unique_donors', 'qualifying']);
  }
  var hist = historySheet.getDataRange().getValues();

  // Upsert today's row so re-running the same day doesn't duplicate
  var todayRow = -1;
  for (var h = 1; h < hist.length; h++) {
    var d = hist[h][0];
    var key = (d instanceof Date) ? Utilities.formatDate(d, tz, 'yyyy-MM-dd') : String(d).trim();
    if (key === today) { todayRow = h + 1; break; }
  }
  var snapshot = [today, totalRaised, rows.length, donorCount, qualifying];
  if (todayRow > 0) {
    historySheet.getRange(todayRow, 1, 1, snapshot.length).setValues([snapshot]);
  } else {
    historySheet.appendRow(snapshot);
  }

  // Week-over-week: compare against the most recent snapshot 7+ days old
  hist = historySheet.getDataRange().getValues();
  var weekAgoTotal = '';
  var weekAgoDonors = '';
  var cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 7);
  var cutoffKey = Utilities.formatDate(cutoff, tz, 'yyyy-MM-dd');
  for (var j = 1; j < hist.length; j++) {
    var dv = hist[j][0];
    var dk = (dv instanceof Date) ? Utilities.formatDate(dv, tz, 'yyyy-MM-dd') : String(dv).trim();
    if (dk && dk <= cutoffKey) {
      weekAgoTotal = hist[j][1];
      weekAgoDonors = hist[j][3];
    }
  }

  // ── Write Summary tab (published as CSV) ──
  var summarySheet = getOrCreateSheet(ss, 'Summary');
  summarySheet.clear();
  summarySheet.appendRow(['metric', 'value']);
  summarySheet.appendRow(['total_raised', totalRaised]);
  summarySheet.appendRow(['donation_count', rows.length]);
  summarySheet.appendRow(['unique_donors', donorCount]);
  summarySheet.appendRow(['average_donation', Math.round(avgDonation * 100) / 100]);
  summarySheet.appendRow(['berkeley_raised', berkeleyRaised]);
  summarySheet.appendRow(['berkeley_donations', berkeleyRows.length]);
  summarySheet.appendRow(['berkeley_donors', berkeleyDonors]);
  summarySheet.appendRow(['qualifying', qualifying]);
  summarySheet.appendRow(['qualified_contributors', qualifiedCount]);
  summarySheet.appendRow(['qualify_min_count', QUALIFY_MIN_COUNT]);
  summarySheet.appendRow(['certify_short', certifyShort]);
  summarySheet.appendRow(['is_certified', isCertified ? 1 : 0]);
  summarySheet.appendRow(['match_earned', matchEarned]);
  summarySheet.appendRow(['match_remaining', matchRemaining]);
  summarySheet.appendRow(['match_cap', MATCH_CAP]);
  summarySheet.appendRow(['match_ratio', MATCH_RATIO]);
  summarySheet.appendRow(['projected_total', projectedTotal]);
  summarySheet.appendRow(['week_ago_total', weekAgoTotal]);
  summarySheet.appendRow(['week_ago_donors', weekAgoDonors]);
  summarySheet.appendRow(['goal_direct', GOAL_DIRECT]);
  summarySheet.appendRow(['goal_total', GOAL_TOTAL]);
  summarySheet.appendRow(['updated', new Date().toISOString()]);

  // Data-freshness metrics. `updated` above only says the script ran — it says
  // nothing about whether it read anything new, which is why a nine-day stall
  // looked like a live figure. These say how stale the underlying reports are.
  // Written as plain numbers/strings so the gviz CSV endpoint can type them.
  summarySheet.appendRow(['reports_read', filesRead]);
  summarySheet.appendRow(['newest_report', newestName || 'NONE']);
  summarySheet.appendRow(['newest_report_date',
    newestTime ? Utilities.formatDate(new Date(newestTime), tz, 'yyyy-MM-dd') : '']);
  summarySheet.appendRow(['data_age_days',
    newestTime ? Math.floor((new Date().getTime() - newestTime) / 86400000) : -1]);

  if (filesRead === 0) {
    Logger.log('WARNING: read 0 report files. Check REPORT_MATCH ("' +
               REPORT_MATCH + '") against the actual filenames in Drive.');
  }

  Logger.log('Consolidated ' + rows.length + ' donations from ' + donorCount +
             ' unique donors. Total: $' + totalRaised);
  Logger.log('Berkeley: $' + berkeleyRaised + ' raised, $' + qualifying +
             ' qualifying -> $' + matchEarned + ' match ($' + matchRemaining + ' left of cap)');
}

function indexOf(arr, label) {
  for (var i = 0; i < arr.length; i++) {
    if (String(arr[i]).trim() === label) return i;
  }
  return -1;
}

function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  // Explicit index rather than the default. Bare insertSheet(name) places the
  // new tab next to whatever SpreadsheetApp considers active, which is not
  // necessarily a tab of `ss` after other spreadsheets have been opened.
  if (!sheet) sheet = ss.insertSheet(name, ss.getNumSheets());
  return sheet;
}
