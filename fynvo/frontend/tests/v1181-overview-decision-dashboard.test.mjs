import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const overview = await read('src/MobileOverviewV1181.jsx');
const app = await read('src/AppV13.jsx');
const main = await read('src/main.jsx');
const css = await read('src/overview-decision-v1181.css');
const config = await read('../config.yaml');
const backendConfig = await read('../backend/app/config.py');
const packageJson = JSON.parse(await read('package.json'));

test('production shell mounts the v1.18.1 Overview implementation', () => {
  assert.match(app, /MobileOverviewV1181/);
  assert.doesNotMatch(app, /<MobileOverviewV1178/);
  assert.match(main, /overview-decision-v1181\.css/);
});

test('Overview follows decision-first mobile hierarchy', () => {
  const before = overview.indexOf('Before next pay');
  const attention = overview.indexOf('Needs attention');
  const needed = overview.indexOf('Money needed soon');
  const cash = overview.indexOf('Cash position');
  const accounts = overview.indexOf('Accounts</h2>');
  const changes = overview.indexOf('What changed?');
  const insights = overview.indexOf('More financial insights');
  for (const value of [before, attention, needed, cash, accounts, changes, insights]) assert.ok(value >= 0);
  assert.ok(before < attention && attention < needed && needed < cash && cash < accounts && accounts < changes && changes < insights);
});

test('Before next pay uses one explicit state and compact stacked metrics', () => {
  for (const label of ['Available now', 'Committed before pay', 'Next income', 'Projected after pay']) assert.match(overview, new RegExp(label));
  assert.match(overview, /Funding information incomplete/);
  assert.doesNotMatch(overview, />UNKNOWN</);
  assert.match(css, /fynvo-overview-v1181-metrics>button/);
  assert.doesNotMatch(css, /fynvo-overview-v1181-metrics\{[^}]*grid-template-columns:1fr 1fr/);
});

test('incomplete funding is explained from authoritative pay-cycle data', () => {
  assert.match(overview, /payCycle\?\.unassigned\?\.commitment_count/);
  assert.match(overview, /payCycle\?\.unassigned\?\.required/);
  assert.match(overview, /no funding account/);
  assert.match(overview, /next_income_known/);
  assert.match(overview, /Fix missing information/);
  assert.match(overview, /missingInfoDestination = model\.unassignedCount > 0 \? 'Payment Centre' : 'Income'/);
});

test('unknown before-pay window never falls back to a 30-day commitment total', () => {
  assert.match(overview, /const beforeCommitments = finite\(before\?\.commitments_total\)/);
  assert.doesNotMatch(overview, /beforeCommitments\) \? beforeCommitments : Number\(planning\?\.periods\?\.next_30_days/);
  assert.match(overview, /model\.commitments === null \? 'Not known' : money\(model\.commitments\)/);
  assert.match(overview, /Next-pay window unavailable/);
});

test('unknown next income also makes projected-after-pay unknown', () => {
  assert.match(overview, /const afterProjected = nextIncomeKnown \? afterProjectedRaw : null/);
  assert.match(overview, /model\.afterProjected === null \? 'Not known' : money\(model\.afterProjected\)/);
  assert.match(overview, /Requires a confirmed next income/);
});

test('loading and unavailable values are not silently presented as zero', () => {
  assert.match(overview, /const \[accounts, setAccounts\] = useState\(null\)/);
  assert.match(overview, /hasCommand/);
  assert.match(overview, /hasAccounts/);
  assert.match(overview, /hasPlanning/);
  assert.match(overview, /model\.attentionCount === null \? '—'/);
  assert.match(overview, /model\.next7 === null \? '—'/);
  assert.match(overview, /model\.totalBalance/);
});

test('Needs attention shows top three exceptions and leaves full workflow in Payment Centre', () => {
  assert.match(overview, /topAttention: sortedAttention\.slice\(0, 3\)/);
  assert.match(overview, /Review all in Payment Centre/);
  assert.match(overview, /attentionRank/);
  assert.match(overview, /overdueCount/);
  assert.match(overview, /unconfirmedCount/);
  assert.match(overview, /incompleteCount/);
});

test('Money needed soon reuses Payment Planning periods and authoritative before-pay commitments', () => {
  assert.match(overview, /planning\?\.periods\?\.next_7_days\?\.remaining_funding/);
  assert.match(overview, /planning\?\.periods\?\.next_30_days\?\.remaining_funding/);
  assert.match(overview, /Before next pay/);
  assert.match(overview, /model\.commitments === null \? 'Not known' : money\(model\.commitments\)/);
});

test('Cash position labels the actual selected range and Accounts stay responsive', () => {
  assert.match(overview, /Cash position/);
  assert.match(overview, /rangeLabel\(rangeDays\)/);
  assert.match(overview, /Income/);
  assert.match(overview, /Spending/);
  assert.match(overview, /Net/);
  assert.match(overview, /topAccounts/);
  assert.match(css, /fynvo-overview-v1181-two-up\{display:grid;grid-template-columns:1fr 1fr/);
  assert.match(css, /@media\(max-width:374px\)/);
  assert.match(css, /fynvo-overview-v1181-two-up\{grid-template-columns:1fr\}/);
});

test('What changed keeps one comparison baseline for the current Overview session', () => {
  assert.match(overview, /fynvo\.overview\.snapshot\.v1181/);
  assert.match(overview, /const \[previousSnapshot\] = useState\(\(\) => readPreviousSnapshot\(\)\)/);
  assert.match(overview, /snapshotWrittenRef/);
  assert.match(overview, /previous Overview snapshot/);
  assert.match(overview, /balanceDelta/);
  assert.match(overview, /commitmentDelta/);
  assert.match(overview, /attentionDelta/);
  assert.doesNotMatch(overview, /setPreviousSnapshot/);
  assert.doesNotMatch(overview, /apiRequest\('\/what-changed/);
});

test('lower-priority outlook is progressively disclosed', () => {
  assert.match(overview, /<details className="fynvo-overview-v1181-insights">/);
  assert.match(overview, /More financial insights/);
  assert.match(overview, /Financial outlook/);
  assert.match(overview, /View full forecast/);
});

test('iPhone and Home Assistant ingress responsive protections remain explicit', () => {
  assert.match(css, /@media\(max-width:980px\)/);
  assert.match(css, /@media\(max-width:430px\)/);
  assert.match(css, /@media\(max-width:374px\)/);
  assert.match(css, /@media\(max-width:329px\)/);
  assert.match(css, /prefers-reduced-motion:reduce/);
  assert.match(css, /body\.fynvo-mobile-overview-active \.dashboard-page\{display:none!important\}/);
});

test('v1.18.1 release versions align', () => {
  assert.match(config, /version: "1\.18\.1"/);
  assert.equal(packageJson.version, '1.18.1');
  assert.match(backendConfig, /APP_VERSION = "1\.18\.1"/);
  assert.match(app, /PRODUCTION_VERSION = '1\.18\.1'/);
});
