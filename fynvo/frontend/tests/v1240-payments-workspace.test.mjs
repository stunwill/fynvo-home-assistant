import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const payments = await read('src/PaymentWorkspaceV1240.jsx');
const css = await read('src/payment-workspace-v1240.css');
const wrapper = await read('src/AppCorrectiveV1163.jsx');

test('Payments provides the approved four-view workspace and default upcoming hierarchy', () => {
  for (const label of ['Upcoming', 'Attention', 'Timeline', 'Manage', 'Next payment', 'Upcoming payments']) assert.match(payments, new RegExp(label));
  assert.match(payments, /fynvo\.payments\.view\.v1240/);
  assert.match(payments, /groupUpcoming/);
  assert.match(payments, /Due within 7 days/);
  assert.match(payments, /Due in 8–30 days/);
  assert.match(payments, /Due later/);
});

test('Payments consolidates attention, resolved history and management destinations', () => {
  for (const label of ['need attention', 'Overdue', 'Action required', 'Resolved recently', 'Recurring schedules', 'Bills and one-off obligations', '＋ Add payment']) assert.match(payments, new RegExp(label));
  assert.match(payments, /requires_action/);
  assert.match(payments, /paymentAttentionReason/);
  assert.match(payments, /onNavigate\('Recurring Expenses'\)/);
  assert.match(payments, /onNavigate\('Bills'\)/);
});

test('Payments preserves valid lifecycle actions and ingress-safe mobile treatment', () => {
  for (const action of ['mark_paid', 'skip', 'change_date', 'edit', 'cancel', 'open_recurring']) assert.match(payments, new RegExp(action));
  assert.match(payments, /scheduled-payments\/\$\{row\.id\}\/skip/);
  assert.match(payments, /scheduled-payments\/\$\{row\.id\}\/reschedule/);
  assert.match(payments, /Change payment date/);
  assert.match(payments, /bills\/\$\{row\.id\}\/mark-paid/);
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /max-width: 430px/);
  assert.match(css, /max-width: 393px/);
  assert.match(css, /max-width: 374px/);
  assert.match(css, /max-width: 329px/);
  assert.match(css, /overflow: auto/);
  assert.match(wrapper, /PaymentWorkspaceV1240/);
});
