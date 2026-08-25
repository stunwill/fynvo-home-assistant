import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const pages = await readFile(new URL('../src/CorrectiveV0174Pages.jsx', import.meta.url), 'utf8');
const app = await readFile(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');
const wrapper = await readFile(new URL('../src/AppV13.jsx', import.meta.url), 'utf8');
const entry = await readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');
const version = await readFile(new URL('../src/v0174-corrective.jsx', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/v018.css', import.meta.url), 'utf8');
const correctiveCss = await readFile(new URL('../src/corrective-v0175.css', import.meta.url), 'utf8');

test('Category management exposes health check and safe merge workflow', () => {
  assert.match(pages, /Check Category Data/);
  assert.match(pages, /Merge Category/);
  assert.match(pages, /\/v018\/categories\/health/);
  assert.match(pages, /\/v018\/categories\/merge\/preview/);
  assert.match(pages, /\/v018\/categories\/merge'/);
  assert.match(pages, /Financial history will not be deleted/);
});

test('zero-entry category rows do not render repeated entry links', () => {
  assert.match(pages, /parent\.entry_count > 0/);
  assert.match(pages, /child\.entry_count > 0/);
  assert.match(pages, /category-count-empty-v018/);
});

test('Recurring Expenses renders authoritative rules before schedule enrichment completes', () => {
  assert.match(pages, /RecurringExpensesPageV151/);
  assert.match(pages, /apiRequest\('\/recurring-expenses'\)/);
  assert.match(pages, /apiRequest\('\/scheduled-payments'\)/);
  assert.doesNotMatch(pages, /apiRequest\('\/payments\/attention'\)/);
  assert.match(pages, /ATTENTION_STATUSES/);
  assert.match(pages, /Loading recurring expenses…/);
  assert.match(pages, /Could not load recurring expenses/);
  assert.match(pages, /setRecurringState\('loaded'\)/);
  assert.match(pages, /RecurringRulesWhileScheduling/);
  assert.match(pages, /scheduled payment information could not be refreshed/);
  assert.match(pages, /const effectiveData = \{ \.\.\.props\.data, recurring: recurringData, scheduledPayments: scheduledData, paymentAttention: attentionData \}/);
});

test('Income keeps the Date Range correction active', () => {
  assert.match(wrapper, /heading === 'Income'/);
  assert.match(wrapper, /classList\.toggle\('fynvo-income-page'/);
  assert.match(correctiveCss, /body\.fynvo-income-page \.header-actions > \.select-shell/);
  assert.match(correctiveCss, /display: none/);
});

test('Overview exposes corrected commitments placement', () => {
  assert.match(app, /Upcoming Commitments/);
  assert.match(app, /Top Planned Spending/);
  assert.match(app, /Financial Health/);
});

test('v0.18 responsive overrides remain active', () => {
  assert.match(entry, /'\.\/v018\.css'/);
  assert.ok(entry.indexOf("'./v018.css'") > entry.indexOf("'./corrective-v0175.css'"));
  assert.match(version, /APP_VERSION_V0174/);
  assert.match(css, /@media\(max-width:980px\)/);
  assert.match(css, /@media\(max-width:600px\)/);
});
