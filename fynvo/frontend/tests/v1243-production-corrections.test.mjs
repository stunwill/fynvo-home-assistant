import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (name) => fs.readFileSync(new URL(`../src/${name}`, import.meta.url), 'utf8');

test('Payments derives attention count and totals from the displayed rows', () => {
  const source = read('PaymentWorkspaceV1240.jsx');
  assert.match(source, /const attentionRows = useMemo/);
  assert.match(source, /const attentionCount = attentionRows\.length/);
  assert.doesNotMatch(source, /setAttentionCount\(/);
  assert.doesNotMatch(source, /requires_action=true/);
});

test('The redesigned Payments workspace suppresses all known legacy mobile shells', () => {
  const css = fs.readFileSync(new URL('../src/payment-workspace-v1240.css', import.meta.url), 'utf8');
  for (const shell of ['payment-centre-page', 'payment-v1161-shell', 'payment-v1182-shell', 'payment-v1183-shell']) {
    assert.match(css, new RegExp(`main\\.content > \\.${shell}`));
  }
});

test('Activity primary data is not restarted by the parent background refresh', () => {
  const source = read('TransactionWorkspace.jsx');
  assert.match(source, /initialRows = null/);
  assert.match(source, /setLoadState\('loaded'\)/);
  assert.match(source, /\[revision, accountId\]/);
  assert.match(source, /optional.*primary request|primary request.*parent/i);
});

test('Accounts passes already-loaded activity into the Activity view', () => {
  const source = read('AccountsWorkspaceV1240.jsx');
  assert.match(source, /initialRows=\{transactions\}/);
  assert.doesNotMatch(source, /refreshKey=\{transactions\.length\}/);
});

test('Calendar validates selected dates before rendering a date heading', () => {
  const source = read('PlanWorkspaceV1240.jsx');
  assert.match(source, /getFullYear\(\) === year/);
  assert.match(source, /selectedCalendarDate = parseDate\(selectedDate\)[\s\S]*\? selectedDate[\s\S]*: localDateKey\(\)/);
  assert.match(source, /dateLabel\(selectedCalendarDate/);
});

test('Safe to Spend exposes a structured unavailable reason and resolution action', () => {
  const backend = fs.readFileSync(new URL('../../backend/app/payment_planning.py', import.meta.url), 'utf8');
  const overview = read('MobileOverviewV1240.jsx');
  const corrections = read('productionCorrectionsV1251.js');
  assert.match(backend, /"unavailable_reason": unavailable_reason/);
  assert.match(backend, /missing_next_income/);
  assert.match(backend, /"action": "income"/);
  assert.match(overview, /unavailable_reason/);
  assert.match(overview, /planningActionV1251/);
  assert.match(corrections, /Review income setup/);
});

test('Planning summaries make the pay-cycle commitment horizon explicit', () => {
  assert.match(read('MobileOverviewV1240.jsx'), /Committed before next pay|Known commitments/);
  assert.match(read('PlanWorkspaceV1240.jsx'), /Committed before next pay/);
});

test('Corrective responsive protections cover the supported iPhone widths', () => {
  const css = fs.readFileSync(new URL('../src/payment-workspace-v1240.css', import.meta.url), 'utf8');
  const accounts = fs.readFileSync(new URL('../src/accounts-workspace-v1240.css', import.meta.url), 'utf8');
  for (const width of ['430px', '393px', '374px', '329px']) assert.match(css, new RegExp(`max-width:\\s*${width}`));
  assert.match(accounts, /safe-area-inset-bottom/);
});
