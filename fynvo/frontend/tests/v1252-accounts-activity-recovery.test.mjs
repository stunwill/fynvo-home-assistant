import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const accounts = await read('src/AccountsWorkspaceV1240.jsx');
const activity = await read('src/TransactionWorkspace.jsx');

test('Accounts Activity supplies the transaction formatter contract', () => {
  assert.match(accounts, /<TransactionWorkspace[^>]*money=\{money\}[^>]*dateLabel=\{dateLabel\}/s);
});

test('Transaction workspace retains safe standalone formatter defaults', () => {
  assert.match(activity, /money\s*=\s*defaultMoney/);
  assert.match(activity, /dateLabel\s*=\s*defaultDateLabel/);
});

test('Accounts Activity remains persisted without making re-entry fatal', () => {
  assert.match(accounts, /fynvo\.accounts\.view\.v1240/);
  assert.match(accounts, /view === "activity"/);
});
