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

test('recurring page performs independent focused loads without a duplicate attention request', () => {
  assert.match(corrective, /const loadRecurring = async/);
  assert.match(corrective, /const loadScheduled = async/);
  assert.match(corrective, /apiRequest\('\/recurring-expenses'\)/);
  assert.match(corrective, /apiRequest\('\/scheduled-payments'\)/);
  assert.doesNotMatch(corrective, /apiRequest\('\/payments\/attention'\)/);
  assert.match(corrective, /ATTENTION_STATUSES\.has\(row\.status\)/);
  assert.match(corrective, /setRecurringState\('loading'\)/);
  assert.match(corrective, /setRecurringState\('loaded'\)/);
  assert.match(corrective, /setRecurringState\('error'\)/);
  assert.match(corrective, /setScheduleState\('loading'\)/);
  assert.match(corrective, /setScheduleState\('loaded'\)/);
  assert.match(corrective, /setScheduleState\('error'\)/);
  assert.match(corrective, /Loading recurring expenses…/);
  assert.match(corrective, /Could not load recurring expenses/);
  assert.doesNotMatch(corrective, /No recurring expenses yet/);
});

test('recurring page composes parent data with authoritative rule and enrichment state only', () => {
  assert.match(corrective, /const recurringData = localRecurring \?\? existingRecurring/);
  assert.match(corrective, /const scheduledData = localScheduled \?\? existingScheduled/);
  assert.match(corrective, /const effectiveData = \{ \.\.\.props\.data, recurring: recurringData, scheduledPayments: scheduledData, paymentAttention: attentionData \}/);
  assert.doesNotMatch(corrective, /setFastData/);
});
