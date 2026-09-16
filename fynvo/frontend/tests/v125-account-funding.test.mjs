import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const accounts = await read('src/AccountsWorkspaceV1240.jsx');
const accountsCss = await read('src/accounts-workspace-v1240.css');
const overview = await read('src/MobileOverviewV1240.jsx');
const plan = await read('src/PlanWorkspaceV1240.jsx');
const productionCorrections = await read('src/productionCorrectionsV1251.js');

test('Accounts exposes authoritative funding states and traceable breakdowns', () => {
  for (const label of ['Covered', 'No payments due', 'Setup needed', 'Until next pay', 'Funding breakdown']) assert.match(accounts, new RegExp(label));
  assert.match(accounts, /funding_shortfall/);
  assert.match(accounts, /payments\s+remaining/);
  assert.match(accounts, /PLANNING_ENDPOINTS_V1251\.accountFunding/);
  assert.match(productionCorrections, /accountFunding:\s*"\/payment-planning\/account-funding\/v1251"/);
  assert.match(accounts, /preferred-buffer/);
  assert.match(accounts, /funding\.commitments/);
});

test('bulk balance workflow preserves entered values and guards unsaved changes', () => {
  for (const label of ['Update balances', 'New balance', 'Changed', 'Save balances', 'Discard balance changes', 'Balances updated']) assert.match(accounts, new RegExp(label));
  assert.match(accounts, /inputMode="decimal"/);
  assert.match(accounts, /onFocus=\{\(event\) => event\.target\.select\(\)\}/);
  assert.match(accounts, /method: "PATCH"/);
  assert.match(accounts, /beforeunload/);
  assert.match(accounts, /Your entries have been kept/);
});

test('balance entry and funding cards protect iPhone layouts and keyboard actions', () => {
  assert.match(accountsCss, /100dvh/);
  assert.match(accountsCss, /safe-area-inset-bottom/);
  assert.match(accountsCss, /overflow: auto/);
  assert.match(accountsCss, /min-width: 0/);
  assert.match(accountsCss, /position: sticky/);
});

test('Overview and Plan share the authoritative Payday Allocation result', () => {
  for (const source of [overview, plan]) assert.match(source, /payday_allocation/);
  assert.match(overview, /Payday allocation/);
  assert.match(overview, /View funding plan/);
  assert.match(plan, /Recommended transfers by account/);
  assert.match(plan, /Already funded/);
  assert.match(plan, /needs a funding\s+account/);
});
