import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('v1.16.3 supplies one combined Accounts and Cards responsive workspace', async () => {
  const page = await read('src/AccountsCardsPageV1163.jsx');
  const workspace = await read('src/AccountsCardsWorkspaceV1163.jsx');
  const wrapper = await read('src/AppCorrectiveV1163.jsx');
  const css = await read('src/accounts-cards-v1163.css');
  assert.match(wrapper, /heading\.textContent = 'Accounts & Cards'/);
  assert.match(wrapper, /Manage your accounts and cards in one place/);
  assert.match(wrapper, /textContent\?\.trim\(\) === 'Cards'\) button\.remove\(\)/);
  assert.match(page, /role="tablist"/);
  assert.match(page, /Search accounts/);
  assert.match(page, /Search cards/);
  assert.match(page, /Linked account:/);
  assert.doesNotMatch(page, /No Cards linked to this Account/);
  assert.match(workspace, /Archive Account/);
  assert.match(workspace, /Move records & archive/);
  assert.match(workspace, /Restore Account/);
  assert.match(workspace, /Edit Account details/);
  assert.match(css, /fynvo-accounts-cards-v1163-active/);
  assert.match(css, /@media\(max-width:1100px\)/);
  assert.match(css, /@media\(max-width:720px\)/);
});

test('Cards view is card-first and active Account selectors exclude archived Accounts', async () => {
  const page = await read('src/AccountsCardsPageV1163.jsx');
  const workspace = await read('src/AccountsCardsWorkspaceV1163.jsx');
  assert.match(page, /Cards \(\{visibleCards\.length\}\)/);
  assert.match(page, /visibleCards\.map\(\(card\)/);
  assert.match(page, /Linked account:/);
  assert.match(workspace, /accounts\.filter\(\(account\) => account\.is_active !== false && !account\.archived_at\)/);
  assert.match(workspace, /Add or restore an active Account before adding a Card/);
});

test('backend account lifecycle preserves historical relationships and protects balance semantics', async () => {
  const source = await read('../backend/app/accounts_cards_v1163.py');
  assert.match(source, /scheduled_payments/);
  assert.match(source, /classification": "historical"/);
  assert.match(source, /transfers_from/);
  assert.match(source, /transfers_to/);
  assert.match(source, /transaction_move_blocked/);
  assert.match(source, /opening balance/);
  assert.match(source, /asset and liability Accounts/);
  assert.match(source, /move-and-archive/);
  assert.match(source, /db\.rollback\(\)/);
  assert.match(source, /cannot be permanently deleted/);
});
