import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const centre = await readFile(new URL('../src/PaymentCentreV112.jsx', import.meta.url), 'utf8');
const model = await readFile(new URL('../src/paymentCentreModel.js', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/payment-centre-v112.css', import.meta.url), 'utf8');
const shell = await readFile(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');


test('Payment Centre exposes occurrence-safe skip and restore actions', () => {
  assert.match(centre, /function SkipPaymentModal/);
  assert.match(centre, /This skips only this payment\. Your recurring schedule will not be changed\./);
  assert.match(centre, /Provider waived payment/);
  assert.match(centre, /User requested skip/);
  assert.match(centre, /`\/scheduled-payments\/\$\{payment\.id\}\/skip`/);
  assert.match(centre, /version: payment\.version/);
  assert.match(centre, /Restore payment/);
  assert.match(centre, /`\/scheduled-payments\/\$\{row\.id\}\/restore`/);
});


test('payment detail uses the focused lifecycle endpoint and closes before actions', () => {
  assert.match(centre, /`\/scheduled-payments\/\$\{row\.id\}\/detail`/);
  assert.match(centre, /const startSkip = \(row\) => \{ setDetail\(null\)/);
  assert.match(centre, /Skip reason/);
  assert.match(centre, /Status history/);
});


test('lifecycle wording and actions are household friendly', () => {
  assert.match(model, /auto_payment_unconfirmed: 'Auto payment unconfirmed'/);
  assert.match(model, /Automatic payment has not been confirmed/);
  assert.match(model, /row\.status === 'skipped'.*'restore'/s);
  assert.match(model, /\['paid', 'cancelled'\]\.includes\(row\.status\)/);
});


test('skip and reschedule modals remain accessible in mobile ingress viewports', () => {
  assert.match(css, /\.payment-centre-reschedule,\.payment-centre-skip\{width:min\(560px,100%\)\}/);
  assert.match(css, /max-height:calc\(100dvh/);
  assert.match(css, /overflow-x:hidden/);
  assert.match(css, /\.payment-centre-reschedule footer,\.payment-centre-skip footer\{position:sticky/);
});


test('production shell reports v1.15.0 and excludes terminal payments from active upcoming commitments', () => {
  assert.match(shell, /const APP_VERSION = '1\.15\.0'/);
  assert.match(shell, /!\['paid', 'skipped', 'cancelled'\]\.includes\(row\.status\)/);
});
