import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const overview = await read('src/MobileOverviewV1178.jsx');
const paymentCentre = await read('src/PaymentCentreV1161.jsx');
const cashFlow = await read('src/CashFlowPageV1161.jsx');
const recurring = await read('src/RecurringExpensesPage.jsx');
const payCycle = await read('src/PayCycleOverviewCard.jsx');
const css = await read('src/mobile-financial-decision-v1180.css');
const config = await read('../config.yaml');
const backendConfig = await read('../backend/app/config.py');

test('mobile Overview leads with authoritative before-pay decision data', () => {
  assert.ok(overview.indexOf('fynvo-mobile-decision') < overview.indexOf('fynvo-mobile-snapshot'));
  assert.match(overview, /planning\?\.pay_cycle/);
  assert.match(overview, /before\.projected_cash/);
  assert.match(overview, /before\.commitments_total/);
  assert.match(overview, /after\.projected_cash/);
  assert.match(overview, /Safe to spend before payday/);
  assert.match(overview, /Funding shortfall/);
  assert.match(overview, /Funding incomplete/);
});

test('mobile Overview prioritises exceptions and groups More navigation', () => {
  assert.match(overview, /Needs attention/);
  assert.match(overview, /payment.*need attention/s);
  for (const group of ['PLAN', 'PAYMENTS', 'MONEY', 'DATA & SYSTEM', 'TOOLS']) assert.match(overview, new RegExp(group.replace('&', '&')));
  assert.match(css, /fynvo-mobile-more-group/);
});

test('Payment Centre interprets funded, shortfall and unknown states', () => {
  assert.match(paymentCentre, /function DecisionSummary/);
  assert.match(paymentCentre, /FUNDING SHORTFALL/);
  assert.match(paymentCentre, /FUNDED BEFORE NEXT PAY/);
  assert.match(paymentCentre, /FUNDING INCOMPLETE/);
  assert.match(paymentCentre, /projected_cash/);
});

test('Payment Centre uses compact mobile filters and explicit incomplete states', () => {
  for (const label of ['Next 30 days', 'Overdue', 'Needs attention', '+ Filters']) assert.ok(paymentCentre.includes(label), `Expected Payment Centre source to include ${label}`);
  assert.match(paymentCentre, /payment-v1180-filter-sheet/);
  assert.match(paymentCentre, /Payment details incomplete: missing/);
  assert.match(paymentCentre, /missing\.push\('due date'\)/);
  assert.match(paymentCentre, /missing\.push\('payment method'\)/);
  assert.match(paymentCentre, /missing\.push\('funding account'\)/);
});

test('Cash Flow states forecast risk and supports chronological or impact ordering', () => {
  assert.match(cashFlow, /Cash shortfall predicted/);
  assert.match(cashFlow, /No cash shortfall is predicted/);
  assert.match(cashFlow, /Lowest projected balance/);
  assert.match(cashFlow, /useState\('next'\)/);
  assert.match(cashFlow, /Largest movements/);
});

test('Recurring Expenses reports overdue aggregates and incomplete payment details', () => {
  assert.match(recurring, /const overdueRows = rows\.filter/);
  assert.match(recurring, /const overdue = \{ count: overdueRows\.length/);
  assert.match(recurring, /const incompleteRows = rows\.filter/);
  assert.match(recurring, /Payment details incomplete: missing/);
  assert.match(recurring, /Needs attention/);
  assert.match(recurring, /navigateReload\('Payment Centre'\)/);
});

test('pay-cycle loading uses a skeleton instead of a textual loading card', () => {
  assert.match(payCycle, /overview-pay-cycle-skeleton/);
  assert.doesNotMatch(payCycle, /Loading cash plan/);
  assert.match(css, /prefers-reduced-motion/);
});

test('mobile decision styles prevent ellipsis and retain responsive narrow-screen fallbacks', () => {
  assert.match(css, /text-overflow:clip!important/);
  assert.match(css, /@media\(max-width:359px\)/);
  assert.match(css, /@media\(max-width:980px\)/);
  assert.match(css, /env\(safe-area-inset-bottom/);
});

test('v1.18.0 add-on and backend versions align', () => {
  assert.match(config, /version: "1\.18\.0"/);
  assert.match(backendConfig, /APP_VERSION = "1\.18\.0"/);
});
