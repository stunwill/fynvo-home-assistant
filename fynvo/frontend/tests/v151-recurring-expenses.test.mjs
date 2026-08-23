import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';

const compatibility = fs.readFileSync(new URL('../src/RecurringExpensesPageV151.jsx', import.meta.url), 'utf8');
const page = fs.readFileSync(new URL('../src/RecurringExpensesPage.jsx', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../src/recurring-v18.css', import.meta.url), 'utf8');

const expectSource = (needle, message) => assert.ok(page.includes(needle), message || `Expected durable RecurringExpensesPage.jsx to contain ${needle}`);

test('v1.5.1 production compatibility now resolves to the durable recurring page', () => {
  assert.match(compatibility, /export \{ default \} from '\.\/RecurringExpensesPage\.jsx'/);
  assert.match(compatibility, /recurring-v18\.css/);
});

test('v1.5.1 search, range, frequency and category filtering remain available', () => {
  for (const text of ['Search expenses...', 'All frequencies', 'All categories', 'Clear filters']) expectSource(text);
  expectSource('export const RANGE_OPTIONS = [7, 14, 30, 60, 90];');
  expectSource("frequency: 'all'");
  expectSource("category: 'all'");
});

test('summary still derives totals, counts and averages from the filtered occurrence set', () => {
  expectSource('const total = rows.reduce((sum, row) => sum + Number(row.expected_amount || 0), 0);');
  expectSource('count: rows.length');
  expectSource('average: rows.length ? total / rows.length : 0');
  expectSource('Breakdown by period');
  expectSource('Largest upcoming expense');
});

test('sorting uses actual Scheduled Payment values', () => {
  expectSource("sort.key === 'amount'");
  expectSource('Number(a.expected_amount || 0) - Number(b.expected_amount || 0)');
  for (const field of ['next_due_date', 'name', 'amount', 'frequency', 'status']) expectSource(`value=\"${field}\"`);
});

test('relative due states remain textual and accessible', () => {
  for (const text of ['Overdue', 'Due today', 'Tomorrow', 'In ${diff} days']) expectSource(text);
  expectSource('aria-label={`Actions for ${payment.name}`}');
  expectSource('role="columnheader"');
});

test('explicit empty states and responsive layouts remain', () => {
  for (const text of ['No recurring expenses yet', 'No expenses match these filters', 'recurring-v18-mobile-list', 'recurring-v18-sheet']) expectSource(text);
  assert.match(css, /@media\(max-width:980px\)/);
  assert.match(css, /\.recurring-v18-table\{display:none\}/);
  assert.match(css, /\.recurring-v18-mobile-list\{display:grid/);
});
