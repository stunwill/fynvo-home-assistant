import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const wrapper = await read('src/AppCorrectiveV1163.jsx');
const shell = await read('src/AppV13.jsx');
const pkg = JSON.parse(await read('package.json'));
const mobile1178 = await read('src/mobile-overview-v1178.css');
const mobile1179 = await read('src/mobile-workspace-v1179.css');


test('Accounts and Cards observer does not rewrite unchanged description text', () => {
  assert.match(wrapper, /const expectedDescription = 'Manage your accounts and cards in one place\.'/);
  assert.match(wrapper, /description && description\.textContent !== expectedDescription/);
  assert.doesNotMatch(wrapper, /if \(description\) description\.textContent = 'Manage your accounts and cards in one place\.'/);
});


test('Accounts and Cards portal mount does not churn identical DOM mount state', () => {
  assert.match(wrapper, /setMount\(\(currentMount\) => currentMount === content \? currentMount : content\)/);
});


test('v1.17.9 production shell owns the visible release version', () => {
  assert.equal(pkg.version, '1.17.9');
  assert.match(shell, /PRODUCTION_VERSION = '1\.17\.9'/);
  assert.match(shell, /const expectedVersion = `Fynvo v\$\{PRODUCTION_VERSION\}`/);
  assert.match(shell, /footer && footer\.textContent !== expectedVersion/);
});


test('mobile Accounts workspace hides irrelevant global controls and stays compact', () => {
  assert.match(mobile1178, /body\.fynvo-accounts-cards-v1163-active main\.content>\.header-actions\{display:none!important\}/);
  assert.match(mobile1178, /accounts-cards-summary\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)!important/);
  assert.match(mobile1179, /accounts-cards-summary article\{min-height:80px!important/);
  assert.match(mobile1178, /accounts-cards-toolbar\{display:grid!important;grid-template-columns:minmax\(0,1fr\) 106px!important/);
  assert.match(mobile1178, /accounts-cards-account-row\{grid-template-columns:38px minmax\(0,1fr\) minmax\(90px,auto\) 12px!important/);
});
