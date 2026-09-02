import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('calendar highlights the local current day without replacing payment status styling', async () => {
  const source = await read('src/RecurringExpensesPage.jsx');
  const css = await read('src/corrective-v1161.css');
  assert.match(source, /const localDateKey =/);
  assert.match(source, /const todayKey = localDateKey\(\)/);
  assert.match(source, /const key = localDateKey\(day\)/);
  assert.match(source, /aria-current=\{isToday \? 'date' : undefined\}/);
  assert.match(source, /isToday \? 'today' : ''/);
  assert.match(source, /calendar-status-\$\{row\.status\}/);
  assert.match(css, /recurring-v18-calendar-grid>button\.today/);
  assert.match(css, /button\.today time/);
});

test('simplified Payment Centre keeps authoritative services and grouped default timeline', async () => {
  const source = await read('src/PaymentCentreV1161.jsx');
  assert.match(source, /apiRequest\(query\)/);
  assert.match(source, /apiRequest\('\/payment-planning'\)/);
  assert.match(source, /Money required for upcoming commitments/);
  assert.match(source, /Upcoming at a glance/);
  assert.match(source, /funding details/i);
  assert.match(source, /More filters/);
  assert.match(source, /Overdue/);
  assert.match(source, /Due in next 7 days/);
  assert.match(source, /Due later/);
  assert.match(source, /No date set/);
  assert.match(source, /GROUP_PREVIEW_COUNT = 3/);
  assert.match(source, /View all \$\{group\.rows\.length\}/);
  assert.match(source, /fynvo\.paymentCentre\.timelineMode/);
  assert.match(source, /<PaymentCentreV112 \{\.\.\.props\}/);
});

test('simplified Payment Centre retains direct mark-paid and full detailed lifecycle access', async () => {
  const source = await read('src/PaymentCentreV1161.jsx');
  assert.match(source, /Mark as paid/);
  assert.match(source, /scheduled-payments\/\$\{row\.id\}\/mark-paid/);
  assert.match(source, /bills\/\$\{row\.id\}\/mark-paid/);
  assert.match(source, /Chronological view/);
  assert.match(source, /paymentPrimaryAction/);
});

test('Cash Flow route restores the forecast graph with explicit request states', async () => {
  const page = await read('src/CashFlowPageV1161.jsx');
  const app = await read('src/AppCorrectiveV0174.jsx');
  assert.match(app, /<CashFlowPageV1161 rangeDays=\{rangeDays\}/);
  assert.match(page, /mode=baseline&horizon=\$\{rangeDays\}d/);
  assert.match(page, /mode=expected&horizon=\$\{rangeDays\}d/);
  assert.match(page, /<CashFlowChartV0174 baseline=\{state\.baseline\} expected=\{state\.expected\}/);
  assert.match(page, /Loading cash flow/);
  assert.match(page, /Cash Flow could not load/);
  assert.match(page, /Retry/);
  assert.match(page, /No forecast events/);
});

test('v1.17.1 production shell is active while legacy compatibility markers remain stable', async () => {
  const app = await read('src/AppCorrectiveV0174.jsx');
  const shell = await read('src/AppV13.jsx');
  const corrective = await read('src/v0174-corrective.jsx');
  const pkg = JSON.parse(await read('package.json'));
  assert.match(app, /APP_VERSION = '1\.17\.0'/);
  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.1'/);
  assert.match(corrective, /APP_VERSION_V0174 = '1\.16\.3'/);
  assert.equal(pkg.version, '1.17.1');
});