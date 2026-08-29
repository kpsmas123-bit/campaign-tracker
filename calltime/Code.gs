/**
 * Call list bridge — paste into the "Call List for Integration" spreadsheet.
 *
 *   Extensions > Apps Script, replace everything with this file, then:
 *   Project Settings > Script Properties > add  SHEET_TOKEN  = <a long random string>
 *   Deploy > New deployment > Web app > Execute as: Me > Access: Anyone
 *
 * "Anyone" is what lets Cloudflare reach this without a Google login. The URL on
 * its own is NOT access: every request must carry SHEET_TOKEN, and the token
 * lives in Script Properties here and in a Cloudflare secret there. It is never
 * in this file, never in the repo, and never sent to the browser — the HQ page
 * talks to /__hq/sheet on its own origin and the edge adds the token.
 *
 * The sheet holds contact PII, so a leaked deployment URL without the token
 * returns 403 and nothing else.
 */

var HEADERS = [
  'Priority', 'Name', 'Email', 'Phone', 'Berkeley',
  'Attempt 1', 'Attempt 2', 'Attempt 3', 'Reached', 'Gave',
  'Gave on', 'Amount', 'Notes', 'Category', 'id (do not edit)'
];
var ID_HEADER = 'id (do not edit)';
var SKIP_TABS = ['READ ME'];

function ok_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
function err_(msg, code) {
  return ok_({ ok: false, error: msg, code: code || 'error' });
}

function checkToken_(supplied) {
  var want = PropertiesService.getScriptProperties().getProperty('SHEET_TOKEN');
  if (!want) return 'SHEET_TOKEN is not set in Script Properties.';
  // Length-then-XOR rather than !==, so a wrong token cannot be walked one
  // character at a time by timing the response.
  var a = String(supplied || ''), b = String(want);
  if (a.length !== b.length) return 'Forbidden.';
  var diff = 0;
  for (var i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0 ? null : 'Forbidden.';
}

function sheets_() {
  var out = [];
  var all = SpreadsheetApp.getActiveSpreadsheet().getSheets();
  for (var i = 0; i < all.length; i++) {
    if (SKIP_TABS.indexOf(all[i].getName()) >= 0) continue;
    out.push(all[i]);
  }
  return out;
}

/** Header name -> 1-based column, read from row 1 rather than assumed. */
function colMap_(sh) {
  var last = Math.max(sh.getLastColumn(), 1);
  var head = sh.getRange(1, 1, 1, last).getValues()[0];
  var map = {};
  for (var i = 0; i < head.length; i++) {
    var k = String(head[i] || '').trim();
    if (k) map[k] = i + 1;
  }
  return map;
}

function rowsOf_(sh) {
  var map = colMap_(sh);
  if (!map[ID_HEADER]) return { map: map, rows: [] };
  var lastRow = sh.getLastRow();
  if (lastRow < 2) return { map: map, rows: [] };
  var lastCol = sh.getLastColumn();
  var values = sh.getRange(2, 1, lastRow - 1, lastCol).getValues();
  var rows = [];
  for (var r = 0; r < values.length; r++) {
    var obj = { _tab: sh.getName(), _row: r + 2 };
    for (var h in map) obj[h] = values[r][map[h] - 1];
    // A row with no id and no name is a blank the user left behind, not a record.
    if (!String(obj[ID_HEADER] || '').trim() && !String(obj['Name'] || '').trim()) continue;
    rows.push(obj);
  }
  return { map: map, rows: rows };
}

function isoDate_(v) {
  if (v instanceof Date) {
    return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  }
  return String(v == null ? '' : v).trim();
}

function readAll_() {
  var tabs = [];
  var shs = sheets_();
  for (var i = 0; i < shs.length; i++) {
    var sh = shs[i];
    var got = rowsOf_(sh);
    var out = [];
    for (var j = 0; j < got.rows.length; j++) {
      var r = got.rows[j];
      out.push({
        id: String(r[ID_HEADER] || '').trim(),
        priority: String(r['Priority'] == null ? '' : r['Priority']).trim(),
        name: String(r['Name'] || ''),
        email: String(r['Email'] || ''),
        phone: String(r['Phone'] || ''),
        berkeley: String(r['Berkeley']).toUpperCase() === 'TRUE' || r['Berkeley'] === true,
        attempts: [isoDate_(r['Attempt 1']), isoDate_(r['Attempt 2']), isoDate_(r['Attempt 3'])],
        gave: String(r['Gave'] || '').toUpperCase() === 'YES',
        gave_on: isoDate_(r['Gave on']),
        gave_amount: r['Amount'] === '' || r['Amount'] == null ? null : Number(r['Amount']),
        notes: String(r['Notes'] || ''),
        category: String(r['Category'] || '')
      });
    }
    tabs.push({ tab: sh.getName(), rows: out });
  }
  return { ok: true, tabs: tabs, at: new Date().toISOString() };
}

function scanFor_(sh, id) {
  var got = rowsOf_(sh);
  for (var j = 0; j < got.rows.length; j++) {
    if (String(got.rows[j][ID_HEADER]).trim() === id) {
      return { sheet: sh, map: got.map, row: got.rows[j]._row };
    }
  }
  return null;
}

/**
 * Locate a row by id. `hint` is the tab the caller last saw it in — checking
 * that first turns the common case into one tab read instead of five, which
 * matters because every edit in the portal lands here. Still falls back to a
 * full scan, since the row may have been dragged to another tab by hand.
 */
function findById_(id, hint) {
  if (hint) {
    var sh = sheetByName_(hint);
    if (sh) {
      var hit = scanFor_(sh, id);
      if (hit) return hit;
    }
  }
  var shs = sheets_();
  for (var i = 0; i < shs.length; i++) {
    if (hint && shs[i].getName() === hint) continue;   // already looked
    var got = scanFor_(shs[i], id);
    if (got) return got;
  }
  return null;
}

function sheetByName_(name) {
  var shs = sheets_();
  for (var i = 0; i < shs.length; i++) if (shs[i].getName() === name) return shs[i];
  return null;
}

/**
 * One read and one write per call, whatever the field count.
 *
 * The obvious loop of sh.getRange(row, col).setValue(v) costs a round trip to
 * the Sheets back end per column, and an attempts update touches four of them.
 * Reading the row once, mutating the array and writing it back once is the
 * documented way to keep this off the execution-time budget.
 */
function writeFields_(sh, map, rowIdx, fields) {
  var width = Math.max(sh.getLastColumn(), 1);
  var row = sh.getRange(rowIdx, 1, 1, width).getValues()[0];
  var touched = false;
  for (var header in fields) {
    var col = map[header];
    if (!col || col > width) continue;   // a column this sheet does not have
    var v = fields[header];
    row[col - 1] = v == null ? '' : v;
    touched = true;
  }
  if (touched) sh.getRange(rowIdx, 1, 1, width).setValues([row]);
}

function doGet(e) {
  var bad = checkToken_(e && e.parameter && e.parameter.token);
  if (bad) return err_(bad, 'forbidden');
  var lock = LockService.getScriptLock();
  try { lock.waitLock(20000); } catch (x) { return err_('Sheet is busy, try again.', 'busy'); }
  try {
    return ok_(readAll_());
  } catch (x) {
    return err_(String(x));
  } finally {
    lock.releaseLock();
  }
}

function doPost(e) {
  var body;
  try { body = JSON.parse(e.postData.contents); }
  catch (x) { return err_('Malformed request body.', 'badrequest'); }

  var bad = checkToken_(body.token);
  if (bad) return err_(bad, 'forbidden');

  var lock = LockService.getScriptLock();
  try { lock.waitLock(20000); } catch (x) { return err_('Sheet is busy, try again.', 'busy'); }

  try {
    if (body.action === 'read') return ok_(readAll_());

    if (body.action === 'update') {
      var hit = findById_(String(body.id || ''), body.from);
      if (!hit) return err_('No row with that id.', 'notfound');

      // A category change is a move between tabs, not a cell edit: read the whole
      // row, append it to the destination, then delete the original. Done in this
      // order so a failure midway leaves a duplicate rather than losing the row.
      if (body.tab && body.tab !== hit.sheet.getName()) {
        var dest = sheetByName_(body.tab);
        if (!dest) return err_('No tab named ' + body.tab, 'notfound');
        var width = hit.sheet.getLastColumn();
        var vals = hit.sheet.getRange(hit.row, 1, 1, width).getValues()[0];
        writeFields_(hit.sheet, hit.map, hit.row, body.fields || {});
        vals = hit.sheet.getRange(hit.row, 1, 1, width).getValues()[0];
        dest.appendRow(vals);
        var dmap = colMap_(dest);
        if (dmap['Category']) dest.getRange(dest.getLastRow(), dmap['Category']).setValue(body.category || body.tab);
        hit.sheet.deleteRow(hit.row);
        return ok_({ ok: true, moved: true, tab: body.tab });
      }

      writeFields_(hit.sheet, hit.map, hit.row, body.fields || {});
      return ok_({ ok: true });
    }

    if (body.action === 'insert') {
      var sh = sheetByName_(body.tab) || sheets_()[0];
      if (!sh) return err_('No writable tab.', 'notfound');
      var map = colMap_(sh);
      var width = Math.max(sh.getLastColumn(), HEADERS.length);
      var line = new Array(width).fill('');
      var f = body.fields || {};
      for (var h in f) if (map[h]) line[map[h] - 1] = f[h] == null ? '' : f[h];
      if (map[ID_HEADER]) line[map[ID_HEADER] - 1] = String(body.id || '');
      sh.appendRow(line);
      return ok_({ ok: true, id: body.id, tab: sh.getName() });
    }

    if (body.action === 'delete') {
      var d = findById_(String(body.id || ''), body.from);
      if (!d) return ok_({ ok: true, already: true });
      d.sheet.deleteRow(d.row);
      return ok_({ ok: true });
    }

    return err_('Unknown action.', 'badrequest');
  } catch (x) {
    return err_(String(x));
  } finally {
    lock.releaseLock();
  }
}
