import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const corrective = fs.readFileSync(new URL('../src/CorrectiveV0174Pages.jsx', import.meta.url), 'utf8');

test('recurring editor normalises optional blank values before generic save', () => {
  assert.match(corrective, /function normaliseNullableRecurringValues/);
  assert.match(corrective, /end_date: nullable\(values\.end_date\)/);
  assert.match(corrective, /reminder_days_before: nullable\(values\.reminder_days_before\)/);
  assert.match(corrective, /account_id: nullable\(values\.account_id\)/);
  assert.match(corrective, /card_id: nullable\(values\.card_id\)/);
  assert.match(corrective, /expense_type_id: nullable\(values\.expense_type_id\)/);
  assert.match(corrective, /values: normaliseNullableRecurringValues\(edit\?\.values \|\| \{\}\)/);
});

test('recurring page performs a focused fast load instead of showing a false empty state', () => {
  assert.match(corrective, /apiRequest\('\/recurring-expenses'\)/);
  assert.match(corrective, /apiRequest\('\/scheduled-payments'\)/);
  assert.match(corrective, /apiRequest\('\/payments\/attention'\)/);
  assert.match(corrective, /setStatus\('loading'\)/);
  assert.match(corrective, /setStatus\('loaded'\)/);
  assert.match(corrective, /setStatus\('error'\)/);
  assert.match(corrective, /Loading recurring expenses…/);
  assert.match(corrective, /Could not load recurring expenses/);
  assert.doesNotMatch(corrective, /No recurring expenses yet/);
});