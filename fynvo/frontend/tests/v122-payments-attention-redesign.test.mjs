import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(new URL('..', import.meta.url).pathname);
const read = (file) => fs.readFile(path.join(root, file), 'utf8');

test('v1.21.2 Overview attention cards expose the approved hierarchy and existing actions', async () => {
  const component = await read('src/PaymentManagementV17.jsx');
  const app = await read('src/AppCorrectiveV0174.jsx');
  const css = await read('src/payments-attention-v122.css');
  assert.match(component, /Payments requiring attention/);
  assert.match(component, /payment\$\{rows\.length === 1 \? '' : 's'\} need review/);
  assert.match(component, /attentionReason\(row\)/);
  assert.match(component, /attentionTiming\(row\.expected_date\)/);
  assert.match(component, /Change payment date/);
  assert.match(component, /Mark as paid/);
  assert.match(component, />Review<\/button>/);
  assert.match(component, /More actions for \$\{row\.name/);
  assert.match(component, /View all \{rows\.length\}/);
  assert.match(app, /paymentCentreRequiresAction/);
  assert.match(css, /@media\(max-width:390px\)/);
  assert.match(css, /grid-template-areas:'main menu' 'amount amount' 'actions actions'/);
  assert.match(css, /payments-attention-v122-menu-popover/);
});

test('v1.21.2 release surfaces are aligned', async () => {
  const pkg = JSON.parse(await read('package.json'));
  const config = await read('../config.yaml');
  const backend = await read('../backend/app/config.py');
  const shell = await read('src/AppV13.jsx');
  assert.equal(pkg.version, '1.21.2');
  assert.match(config, /version: "1\.21\.2"/);
  assert.match(backend, /APP_VERSION = "1\.21\.2"/);
  assert.match(shell, /PRODUCTION_VERSION = '1\.21\.2'/);
});
