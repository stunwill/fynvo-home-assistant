import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const apiClient = fs.readFileSync(new URL('../src/apiClient.js', import.meta.url), 'utf8');
const recurringPages = fs.readFileSync(new URL('../src/CorrectiveV0174Pages.jsx', import.meta.url), 'utf8');
const app = fs.readFileSync(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');

test('canonical API client uses ingress-safe relative paths', () => {
  assert.match(apiClient, /return `api\/\$\{clean\}`/);
  assert.doesNotMatch(apiClient, /fetch\('\/api\//);
  assert.match(apiClient, /credentials: 'same-origin'/);
});

test('recurring expenses distinguishes loading error and loaded states', () => {
  assert.match(recurringPages, /setStatus\('loading'\)/);
  assert.match(recurringPages, /setStatus\('loaded'\)/);
  assert.match(recurringPages, /setStatus\('error'\)/);
  assert.match(recurringPages, /Loading recurring expenses…/);
  assert.match(recurringPages, /Could not load recurring expenses/);
  assert.match(recurringPages, />Retry</);
});

test('recurring mutations normalize nullable values before save', () => {
  for (const field of ['account_id', 'card_id', 'category_id', 'expense_type_id', 'end_date', 'reminder_days_before', 'effective_from']) {
    assert.ok(app.includes(`${field}: nullable(values.${field})`));
  }
  assert.match(app, /const values = normaliseMutationValues\(edit\.type, edit\.values\)/);
});

test('recurring save uses focused refresh instead of blocking on all application data', () => {
  assert.match(app, /async function refreshRecurringSlice\(\)/);
  assert.match(app, /if \(edit\.type === 'recurring'\) await refreshRecurringSlice\(\)/);
});

test('feature errors clear on navigation', () => {
  assert.match(app, /setSuccess\(''\); setError\(''\);/);
});
