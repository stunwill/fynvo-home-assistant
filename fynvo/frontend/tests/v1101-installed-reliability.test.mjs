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

test('recurring page can render existing authoritative data while refreshing', () => {
  assert.match(pages, /const hasExistingData = existingRecurring\.length > 0 \|\| existingScheduled\.length > 0/);
  assert.match(pages, /useState\(hasExistingData \? 'loaded' : 'loading'\)/);
  assert.match(pages, /const effectiveData = \{ \.\.\.props\.data, \.\.\.\(fastData \|\| \{\}\) \}/);
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
