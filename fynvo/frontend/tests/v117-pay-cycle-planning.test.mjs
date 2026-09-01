import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const app = fs.readFileSync(path.join(root, 'src/AppCorrectiveV0174.jsx'), 'utf8');
const overview = fs.readFileSync(path.join(root, 'src/PayCycleOverviewCard.jsx'), 'utf8');
const overviewCss = fs.readFileSync(path.join(root, 'src/pay-cycle-overview.css'), 'utf8');
const centre = fs.readFileSync(path.join(root, 'src/PaymentCentreV1161.jsx'), 'utf8');
const centreCss = fs.readFileSync(path.join(root, 'src/payment-centre-v112.css'), 'utf8');
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));


test('v1.17 pay-cycle implementation remains active on the v1.17.1 corrective patch', () => {
  assert.equal(pkg.version, '1.17.1');
  assert.match(app, /const APP_VERSION = '1\.17\.0'/);
});


test('Overview renders a Before next pay summary with explicit states and drill-through', () => {
  assert.match(app, /PayCycleOverviewCard/);
  assert.match(overview, /Before next pay/);
  assert.match(overview, /Loading cash plan/);
  assert.match(overview, /Next income not known/);
  assert.match(overview, /No commitments are due before the next pay/);
  assert.match(overview, /Need before pay/);
  assert.match(overview, /Available cash/);
  assert.match(overview, /Projected before pay/);
  assert.match(overview, /After next pay/);
  assert.match(overview, /Open Payment Centre/);
  assert.match(overview, /Shortfall/);
  assert.match(overview, /Unknown/);
});


test('Payment Centre has operational pay-cycle states and account pressure', () => {
  assert.match(centre, /PayCycleSummary/);
  assert.match(centre, /Loading before-next-pay plan/);
  assert.match(centre, /Next income not known/);
  assert.match(centre, /Accounts needing attention/);
  assert.match(centre, /All assigned Accounts are funded/);
  assert.match(centre, /Shortfall/);
  assert.match(centre, /Funding unknown/);
  assert.match(centre, /Income is applied before commitments on the same date/);
  assert.match(centre, /apiRequest\('\/payment-planning'\)/);
  assert.doesNotMatch(centre, /apiRequest\('\/payment-planning\/pay-cycle'\)/);
});


test('responsive pay-cycle layouts stack without requiring a wide desktop table', () => {
  assert.match(overviewCss, /@media\(max-width:620px\)/);
  assert.match(overviewCss, /grid-template-columns:1fr 1fr/);
  assert.match(overviewCss, /@media\(max-width:390px\)/);
  assert.match(overviewCss, /grid-template-columns:1fr/);
  assert.match(centreCss, /\.pay-cycle-panel[^}]*overflow:hidden/);
  assert.match(centreCss, /@media\(max-width:620px\)/);
  assert.match(centreCss, /\.pay-cycle-metrics\{grid-template-columns:1fr 1fr\}/);
  assert.match(centreCss, /\.payment-centre-page\{[^}]*overflow-x:hidden/);
});


test('Calendar prioritises reconciled command-centre calendar events', () => {
  assert.match(app, /command\?\.calendar \|\| command\?\.upcoming_commitments/);
});