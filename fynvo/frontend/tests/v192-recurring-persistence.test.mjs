import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const app = fs.readFileSync(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');
const payment = fs.readFileSync(new URL('../src/PaymentManagementV17.jsx', import.meta.url), 'utf8');

test('new account choices are limited to Transaction Account and Cash', () => {
  const block = app.slice(app.indexOf('const accountTypeOptions'), app.indexOf('const recordLabels'));
  assert.match(block, /Transaction Account/);
  assert.match(block, /Cash/);
  for (const removed of ['Savings Account', 'Offset Account', 'Credit Card', 'Mortgage', 'Personal Loan', 'Car Loan', 'Line of Credit', 'Investment Account', 'Superannuation', 'Other Asset', 'Other Liability']) {
    assert.doesNotMatch(block, new RegExp(removed));
  }
});

test('account form labels institution as Bank', () => {
  assert.match(app, /text\('institution', 'Bank'\)/);
});

test('recurring Expense Type uses authoritative reference data dropdown', () => {
  assert.match(app, /j\('\/reference-data'\)/);
  assert.match(app, /expenseTypes/);
  assert.match(app, /Choose Expense Type/);
  assert.match(app, /expense_type_id/);
});

test('automatic payment confirmation period is explained and remains conditional', () => {
  assert.match(payment, /Payment confirmation period/);
  assert.match(payment, /How long Fynvo should wait after the due date for an automatic payment to be confirmed/);
  assert.match(payment, /values\.payment_handling === 'automatic'/);
});

test('newly saved card is rendered immediately before parent refresh completes', () => {
  assert.match(payment, /const \[localCards, setLocalCards\] = useState\(cards\)/);
  assert.match(payment, /setLocalCards\(\(current\)/);
  assert.match(payment, /await onRefresh\(\)/);
});

test('recurring quick-add uses nullable payment references', () => {
  assert.match(app, /\{ account_id: null, card_id: null \}/);
});
