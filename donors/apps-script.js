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
var REPORT_MATCH = 'custom-report-report1.1'; // Substring found in every report filename

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
 * Move ActBlue reports out of Drive root into the reports folder.
 * ActBlue names reports like
 *   daria-wrubel-233102-custom-report-report1.1-2026-07-01-2026-07-28
 * so REPORT_MATCH is matched anywhere in the name, not just at the start.
 * Run before consolidate().
 */
function moveReportsToFolder() {
  var folder = getReportsFolder();
  var root = DriveApp.getRootFolder();
  var moved = 0;

  [MimeType.GOOGLE_SHEETS, MimeType.CSV].forEach(function(type) {
    var files = root.getFilesByType(type);
    while (files.hasNext()) {
      var file = files.next();
      if (isReport(file.getName())) {
        file.moveTo(folder);
        moved++;
        Logger.log('Moved: ' + file.getName());
      }
    }
  });

  Logger.log('Moved ' + moved + ' report(s) into "' + FOLDER_NAME + '"');
}

function consolidate() {
  moveReportsToFolder();
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // Collect all rows from every sheet in the folder
  var folder = getReportsFolder();
  var files = folder.getFilesByType(MimeType.GOOGLE_SHEETS);
  var seen = {};   // Lineitem ID -> row
  var rows = [];

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
  if (!sheet) sheet = ss.insertSheet(name);
  return sheet;
}
