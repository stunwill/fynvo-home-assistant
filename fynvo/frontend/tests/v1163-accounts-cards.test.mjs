import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('v1.16.3 supplies a combined Accounts and Cards responsive workspace', async () => {
  const page = await read('src/AccountsCardsPageV1163.jsx');
  const workspace = await read('src/AccountsCardsWorkspaceV1163.jsx');
  const css = await read('src/accounts-cards-v1163.css');
  assert.match(page, /Accounts &amp; Cards/);
  assert.match(page, /role="tablist"/);
  assert.match(page, /Search accounts/);
  assert.match(page, /Search cards/);
  assert.match(page, /Linked account:/);
  assert.doesNotMatch(page, /No Cards linked to this Account/);
  assert.match(workspace, /Archive Account/);
  assert.match(workspace, /Move records & archive/);
  assert.match(workspace, /Restore Account/);
  assert.match(css, /@media\(max-width:1100px\)/);
  assert.match(css, /@media\(max-width:720px\)/);
});

test('backend account lifecycle preserves historical relationships', async () => {
  const source = await read('../backend/app/accounts_cards_v1163.py');
  assert.match(source, /scheduled_payments/);
  assert.match(source, /classification": "historical"/);
  assert.match(source, /transfers_from/);
  assert.match(source, /transfers_to/);
  assert.match(source, /move-and-archive/);
  assert.match(source, /db\.rollback\(\)/);
  assert.match(source, /cannot be permanently deleted/);
});
