import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const app = fs.readFileSync(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');
const centre = fs.readFileSync(new URL('../src/PaymentCentreV112.jsx', import.meta.url), 'utf8');
const model = fs.readFileSync(new URL('../src/paymentCentreModel.js', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../src/payment-centre-v112.css', import.meta.url), 'utf8');

const planningService = fs.readFileSync(new URL('../../backend/app/payment_planning.py', import.meta.url), 'utf8');


test('Overview and Payment Centre both consume the shared payment planning service', () => {
  assert.match(app, /j\('\/payment-planning'\)/);
  assert.match(app, /paymentPlanning\.money_needed_soon\?\.next_7_days/);
  assert.match(app, /paymentPlanning\.money_needed_soon\?\.next_30_days/);
  assert.doesNotMatch(app, /function withinDays/);
  assert.doesNotMatch(app, /function paymentTotal/);
  assert.match(centre, /apiRequest\('\/payment-planning'\)/);
  assert.match(centre, /Money required for upcoming commitments/);
});


test('payment planning documents funding rules and excludes terminal states', () => {
  assert.match(planningService, /automatic_payments_require_funding/);
  assert.match(planningService, /TERMINAL_STATUSES = \{"paid", "skipped", "cancelled"\}/);
  assert.match(planningService, /Account not specified/);
  assert.match(planningService, /LIQUID_ACCOUNT_TYPES/);
  assert.match(planningService, /Unknown or liability balances are never treated as zero/);
});


test('Payment Centre exposes planning periods, account funding and chronological grouping', () => {
  for (const label of ['Today', 'Next 7 days', 'Next 14 days', 'Next 30 days', 'This month', 'Next month']) {
    assert.ok(model.includes(label), `missing date-range label: ${label}`);
  }
  assert.match(model, /export function groupPaymentsByDate/);
  assert.match(model, /Today/);
  assert.match(model, /Tomorrow/);
  assert.match(centre, /Money needed by account/);
  assert.match(centre, /Available funds vs commitments/);
  assert.match(centre, /Likely shortfall|shortfall/);
  assert.match(centre, /Payment timeline/);
});


test('status and attention wording is explicit and not colour-only', () => {
  for (const label of ['Upcoming', 'Due today', 'Overdue', 'Expected automatically', 'Confirmation needed', 'Paid', 'Skipped', 'Cancelled']) {
    assert.ok(model.includes(label), `missing payment status label: ${label}`);
  }
  for (const reason of ['Reconciliation ambiguity', 'Automatic payment not confirmed', 'Missing payment method', 'Missing funding account', 'Manual payment due']) {
    assert.ok(model.includes(reason), `missing attention reason: ${reason}`);
  }
  assert.match(centre, /<StatusBadge status=\{row\.status\}/);
});


test('payment detail includes lifecycle evidence while omitting empty optional fields', () => {
  assert.match(centre, /Original occurrence date/);
  assert.match(centre, /Current expected date/);
  assert.match(centre, /Actual payment date/);
  assert.match(centre, /Funding account/);
  assert.match(centre, /Lifecycle history/);
  assert.match(centre, /Matched transaction/);
  assert.match(centre, /detail\.card_name &&/);
  assert.match(centre, /detail\.actual_date &&/);
});


test('mobile planning and modal containment protect ingress and iPhone layouts', () => {
  assert.match(css, /overflow-x:hidden/);
  assert.match(css, /max-width:100%/);
  assert.match(css, /env\(safe-area-inset-bottom\)/);
  assert.match(css, /max-height:calc\(100dvh/);
  assert.match(css, /payment-centre-mark-paid footer\{position:sticky/);
  assert.match(css, /white-space:normal;overflow-wrap:anywhere/);
  assert.match(centre, /setDetail\(null\); setMarkingPaid/);
  assert.match(centre, /setDetail\(null\); setRescheduling/);
  assert.match(centre, /const startSkip = \(row\) => \{ setDetail\(null\); setActionError\(''\); setSkipping\(row\); \}/);
});


test('production version reports v1.16.3', () => {
  assert.match(app, /APP_VERSION = '1\.16\.3'/);
});
