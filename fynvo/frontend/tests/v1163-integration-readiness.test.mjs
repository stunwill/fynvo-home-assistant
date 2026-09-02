import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');

test('production shell mounts the v1.16.3 Accounts and Cards correction', async () => {
  const shell = await read('src/AppV13.jsx');
  const wrapper = await read('src/AppCorrectiveV1163.jsx');
  const entry = await read('src/main.jsx');

  assert.match(shell, /import App from '\.\/AppCorrectiveV1163\.jsx'/);
  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.1'/);
  assert.match(entry, /import '\.\/accounts-cards-v1163\.css';/);
  assert.match(wrapper, /fynvo-accounts-cards-v1163-active/);
  assert.match(wrapper, /onViewChange=\{setSubview\}/);
});

test('combined workspace exposes active account lifecycle management and safe card selectors', async () => {
  const workspace = await read('src/AccountsCardsWorkspaceV1163.jsx');
  assert.match(workspace, /onEditAccount=\{startManage\}/);
  assert.match(workspace, /Edit Account details/);
  assert.match(workspace, /Archive Account/);
  assert.match(workspace, /Move records & archive/);
  assert.match(workspace, /transaction_move_blocked/);
  assert.match(workspace, /account\.is_active !== false && !account\.archived_at/);
});

test('legacy Accounts and Cards content is suppressed while the combined workspace is active', async () => {
  const css = await read('src/accounts-cards-v1163.css');
  assert.match(css, /fynvo-accounts-cards-v1163-active main\.content>section\{display:none!important\}/);
  assert.match(css, /main\.content>\.accounts-cards-v1163-overlay\{display:block!important\}/);
});
