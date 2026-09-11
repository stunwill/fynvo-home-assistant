import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const plan = await read('src/PlanWorkspaceV1240.jsx');
const css = await read('src/plan-workspace-v1240.css');
const wrapper = await read('src/AppCorrectiveV1163.jsx');

test('Plan provides Overview, Forecast and Calendar views', () => {
  for (const label of ['Plan', 'Overview', 'Forecast', 'Calendar', 'Projected balance', 'Balance trajectory']) assert.match(plan, new RegExp(label));
  assert.match(plan, /fynvo\.plan\.view\.v1240/);
  assert.match(plan, /fynvo\.plan\.horizon\.v1240/);
});

test('Plan uses authoritative planning and forecast responses', () => {
  assert.match(plan, /payment-planning/);
  assert.match(plan, /payment-planning\/safe-to-spend/);
  assert.match(plan, /forecast\?mode=expected/);
  assert.match(plan, /forecast\?mode=baseline/);
  for (const label of ['available_cash', 'committed_outgoings', 'protected_buffer', 'income_total', 'expense_total', 'shortfall', 'lowest_balance']) assert.match(plan, new RegExp(label));
});

test('Plan distinguishes pressure, income, payments and healthy states', () => {
  for (const label of ['Upcoming pressure point', 'Healthy trajectory', 'Incoming income', 'Total income', 'Total expenses', 'Projected shortfall', 'eventType']) assert.match(plan, new RegExp(label));
  assert.match(plan, /View all payments for this date/);
  assert.match(plan, /onNavigate\('Payments'\)/);
});

test('Calendar supports month navigation, selected dates and event markers', () => {
  for (const label of ['Previous month', 'Next month', 'selectedDate', 'calendar-grid', 'income', 'attention', 'payment']) assert.match(plan, new RegExp(label));
});

test('Plan mobile shell protects ingress widths and safe areas', () => {
  assert.match(css, /safe-area-inset-bottom/);
  for (const width of ['430px', '393px', '374px', '329px']) assert.match(css, new RegExp(`max-width: ${width}`));
  assert.match(css, /min-width: 0/);
  assert.match(css, /overflow/);
  assert.match(wrapper, /PlanWorkspaceV1240/);
  assert.match(wrapper, /planActive/);
});
