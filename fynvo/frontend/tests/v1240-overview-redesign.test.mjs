import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const overview = await read('src/MobileOverviewV1240.jsx');
const foundation = await read('src/fynvo-ui-foundation.css');
const css = await read('src/mobile-overview-v1240.css');

test('Overview follows the approved four-part hierarchy without Accounts duplication', () => {
  assert.match(overview, /Safe to spend/);
  assert.match(overview, /Needs attention/);
  assert.match(overview, /Coming up/);
  assert.match(overview, /Your plan/);
  assert.doesNotMatch(overview, /Accounts at a glance/);
  assert.doesNotMatch(overview, /Money requiring action/);
});

test('Overview uses real planning states and links to later destinations', () => {
  assert.match(overview, /safeAvailable/);
  assert.match(overview, /Unavailable/);
  assert.match(overview, /open\('Payments'\)/);
  assert.match(overview, /open\('Plan'\)/);
  assert.match(overview, /No payments need your attention right now/);
  assert.match(overview, /No upcoming payments/);
});

test('shared foundation and mobile shell protect narrow ingress layouts', () => {
  assert.match(foundation, /min-width: 0/);
  assert.match(foundation, /overflow-wrap: anywhere/);
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /max-width: 430px/);
  assert.match(css, /max-width: 374px/);
  assert.match(css, /max-width: 329px/);
});

test('More keeps secondary tools discoverable without duplicating redesigned destinations', () => {
  assert.match(overview, /open\('Categories'\)/);
  assert.match(overview, /open\('CSV Import'\)/);
  assert.match(overview, /open\('Review Queue'\)/);
  assert.doesNotMatch(overview, />Cash Flow<\/button>/);
  assert.doesNotMatch(overview, />Calendar<\/button>/);
  assert.doesNotMatch(overview, />Transactions<\/button>/);
  assert.doesNotMatch(overview, />Recurring Expenses<\/button>/);
});
