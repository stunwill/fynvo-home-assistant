import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const accounts = await read('src/AccountsWorkspaceV1240.jsx');
const activity = await read('src/TransactionWorkspace.jsx');
const core = await read('src/TransactionWorkspaceCore.jsx');

test('Accounts Activity routes through the protected transaction workspace', () => {
  assert.match(accounts, /view === "activity"/);
  assert.match(accounts, /<TransactionWorkspace/);
  assert.match(activity, /TransactionWorkspaceCore/);
});

test('Transaction workspace supplies safe formatter defaults', () => {
  assert.match(activity, /money\s*=\s*defaultMoney/);
  assert.match(activity, /dateLabel\s*=\s*defaultDateLabel/);
  assert.match(activity, /money=\{money\}/);
  assert.match(activity, /dateLabel=\{dateLabel\}/);
});

test('Activity keeps the existing transaction and reconciliation implementation', () => {
  assert.match(core, /payments\/transactions\?limit=2000/);
  assert.match(core, /payments\/match-candidates/);
  assert.match(core, /Possible payment matches/);
});

test('Accounts Activity remains persisted without making re-entry fatal', () => {
  assert.match(accounts, /fynvo\.accounts\.view\.v1240/);
});
