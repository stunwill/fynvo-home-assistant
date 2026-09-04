import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const wrapper = await read('src/AppCorrectiveV1163.jsx');
const shell = await read('src/AppV13.jsx');
const pkg = JSON.parse(await read('package.json'));


test('Accounts and Cards observer does not rewrite unchanged description text', () => {
  assert.match(wrapper, /const expectedDescription = 'Manage your accounts and cards in one place\.'/);
  assert.match(wrapper, /description && description\.textContent !== expectedDescription/);
  assert.doesNotMatch(wrapper, /if \(description\) description\.textContent = 'Manage your accounts and cards in one place\.'/);
});


test('Accounts and Cards portal mount does not churn identical DOM mount state', () => {
  assert.match(wrapper, /setMount\(\(currentMount\) => currentMount === content \? currentMount : content\)/);
});


test('v1.17.7 production shell owns the visible release version', () => {
  assert.equal(pkg.version, '1.17.7');
  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.7'/);
  assert.match(shell, /const expectedVersion = `Fynvo v\$\{PRODUCTION_VERSION\}`/);
  assert.match(shell, /footer && footer\.textContent !== expectedVersion/);
});
