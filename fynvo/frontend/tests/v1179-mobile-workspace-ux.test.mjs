import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const overview = await read('src/MobileOverviewV1178.jsx');
const css = await read('src/mobile-workspace-v1179.css');
const cashFlow = await read('src/CashFlowPageV1161.jsx');
const transactions = await read('src/TransactionWorkspace.jsx');
const appShell = await read('src/AppV13.jsx');
const entry = await read('src/main.jsx');
const pkg = JSON.parse(await read('package.json'));

test('v1.17.9 Overview follows the supplied mobile hierarchy and human-readable range labels', () => {
  const snapshotIndex = overview.indexOf('fynvo-mobile-snapshot');
  const cashIndex = overview.indexOf('fynvo-mobile-cashflow');
  const accountsIndex = overview.indexOf('fynvo-mobile-accounts');
  assert.ok(snapshotIndex >= 0 && cashIndex > snapshotIndex && accountsIndex > cashIndex);
  const snapshot = overview.match(/fynvo-mobile-snapshot-grid[\s\S]*?<\/div>\s*<\/section>/)?.[0] || '';
  assert.equal((snapshot.match(/<button/g) || []).length, 4);
  assert.match(overview, /184: 'Next 6 months'/);
  assert.match(overview, /rangeLabel\(rangeDays\)/);
  assert.match(overview, /data-icon=/);
});

test('Overview currency values are protected from isolated-digit wrapping', () => {
  assert.match(css, /fynvo-mobile-snapshot-grid strong[^}]*white-space:nowrap/);
  assert.match(css, /fynvo-mobile-cashflow-card strong[^}]*white-space:nowrap/);
  assert.match(overview, /compactMoney\(model\.inflow\)/);
  assert.match(overview, /compactMoney\(model\.outflow\)/);
  assert.match(overview, /compactMoney\(model\.net\)/);
});

test('Overview retains canonical API client and top three active accounts', () => {
  assert.match(overview, /apiRequest\(`\/dashboard\/command-centre\?range_days=\$\{rangeDays\}`\)/);
  assert.match(overview, /apiRequest\('\/accounts'\)/);
  assert.match(overview, /apiRequest\('\/payment-planning'\)/);
  assert.match(overview, /account\.is_active !== false && !account\.archived_at/);
  assert.match(overview, /\.slice\(0, 3\)/);
});

test('Cash Flow chart has explicit no-fill series styling and separated legend', () => {
  assert.match(css, /cashflow-chart-v0174 svg path\{fill:none!important/);
  assert.match(css, /svg path\.baseline\{stroke:#155eef/);
  assert.match(css, /svg path\.expected\{stroke:#079455/);
  assert.match(css, /cashflow-chart-legend span\{display:inline-flex/);
});

test('Cash Flow defaults to five impact events with full-list disclosure', () => {
  assert.match(cashFlow, /slice\(0, 5\)/);
  assert.match(cashFlow, /View all \$\{events\.length\} events/);
  assert.match(cashFlow, /Show less/);
  assert.match(cashFlow, /184: 'Next 6 months'/);
});

test('Transactions uses mobile Search + period + Filters and preserves secondary filters in a sheet', () => {
  assert.match(transactions, /transaction-mobile-filter-trigger/);
  assert.match(transactions, /transaction-mobile-filter-sheet/);
  for (const label of ['Account filter', 'Category filter', 'Transaction type filter', 'Reconciliation filter', 'Transaction source filter']) assert.match(transactions, new RegExp(label));
  assert.match(transactions, /const activeSecondaryFilters = \['account', 'category', 'type', 'reconciliation', 'source'\]\.filter/);
  assert.match(transactions, /Filters\{activeSecondaryFilters \? ` \(\$\{activeSecondaryFilters\}\)` : ''\}/);
  assert.match(css, /fynvo-transactions-page \.transaction-desktop-secondary-filters\{display:none!important\}/);
});

test('specialised mobile workspaces suppress redundant global header actions', () => {
  assert.match(css, /fynvo-accounts-cards-v1163-active main\.content>\.header-actions/);
  assert.match(css, /fynvo-transactions-page main\.content>\.header-actions/);
  assert.match(css, /fynvo-recurring-expenses-page main\.content>\.header-actions/);
  assert.match(appShell, /fynvo-transactions-page/);
  assert.match(appShell, /fynvo-recurring-expenses-page/);
});

test('v1.17.9 stylesheet is final and production version surfaces agree', () => {
  assert.match(entry, /import '\.\/mobile-workspace-v1179\.css';\s*\n\nReactDOM/s);
  assert.equal(pkg.version, '1.17.9');
  assert.match(appShell, /PRODUCTION_VERSION = '1\.17\.9'/);
});
