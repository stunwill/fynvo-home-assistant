import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const pages = fs.readFileSync(new URL('../src/CorrectiveV0174Pages.jsx', import.meta.url), 'utf8');
const app = fs.readFileSync(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');
const payments = fs.readFileSync(new URL('../src/PaymentManagementV17.jsx', import.meta.url), 'utf8');

test('recurring page derives attention from the authoritative scheduled-payment response', () => {
  assert.match(pages, /ATTENTION_STATUSES = new Set/);
  assert.match(pages, /apiRequest\('\/scheduled-payments'\)/);
  assert.doesNotMatch(pages, /apiRequest\('\/payments\/attention'\)/);
  assert.match(pages, /filter\(\(row\) => ATTENTION_STATUSES\.has\(row\.status\)\)/);
});

test('recurring rules load independently from scheduled-payment enrichment', () => {
  assert.match(pages, /const loadRecurring = async/);
  assert.match(pages, /const loadScheduled = async/);
  assert.match(pages, /setRecurringState\('loaded'\)/);
  assert.match(pages, /setScheduleState\('loaded'\)/);
  assert.doesNotMatch(pages, /Promise\.all\(\[\s*apiRequest\('\/recurring-expenses'\),\s*apiRequest\('\/scheduled-payments'\)/s);
  assert.match(pages, /RecurringRulesWhileScheduling/);
  assert.match(pages, /Recurring expenses are available, but scheduled payment information could not be refreshed/);
  assert.match(pages, /retrySchedule/);
});

test('recurring mutation uses canonical API request and normalises nullable references', () => {
  assert.match(app, /apiRequest\(path, \{ method: creating \? 'POST' : 'PUT'/);
  for (const field of ['account_id', 'card_id', 'category_id', 'expense_type_id', 'end_date', 'reminder_days_before', 'effective_from']) {
    assert.ok(app.includes(`${field}: nullable(values.${field})`));
  }
});

test('payment controls preserve canonical payment fields', () => {
  assert.match(payments, /payment_handling/);
  assert.match(payments, /payment_method/);
  assert.match(payments, /auto_payment_grace_days/);
  assert.match(payments, /Linked to account:/);
});
