import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const centre = await readFile(new URL('../src/PaymentCentreV112.jsx', import.meta.url), 'utf8');
const attention = await readFile(new URL('../src/PaymentManagementV17.jsx', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/payment-centre-v112.css', import.meta.url), 'utf8');

test('Payment Centre exposes one-off date change and restore without editing the recurring series', () => {
  assert.match(centre, /Change payment date/);
  assert.match(centre, /Restore original date/);
  assert.match(centre, /This changes only this payment\. Your recurring schedule will not be changed\./);
  assert.match(centre, /\/scheduled-payments\/\$\{payment\.id\}\/reschedule/);
  assert.match(centre, /\/scheduled-payments\/\$\{row\.id\}\/restore-original-date/);
  assert.match(centre, /original_expected_date/);
  assert.match(centre, /is_date_overridden/);
  assert.match(centre, /setDetail\(null\); setRescheduling\(row\)/);
});

test('Payments requiring attention can reschedule a failed or unconfirmed occurrence', () => {
  assert.match(attention, /Change payment date/);
  assert.match(attention, /\/scheduled-payments\/\$\{payment\.id\}\/reschedule/);
  assert.match(attention, /Insufficient funds/);
  assert.match(attention, /Payment deferred/);
  assert.match(attention, /setReviewing\(null\); setPaying\(null\); setRescheduling\(row\)/);
  assert.match(attention, /Your recurring schedule will not be changed/);
});

test('occurrence editor remains contained and keeps actions accessible on mobile', () => {
  assert.match(css, /\.payment-centre-reschedule,\.payment-centre-skip\{width:min\(560px,100%\)/);
  assert.match(css, /@media\(max-width:620px\)[\s\S]*\.payment-centre-detail,.payment-centre-mark-paid\{[^}]*overflow-x:hidden/);
  assert.match(css, /@media\(max-width:620px\)[\s\S]*\.payment-centre-reschedule footer,\.payment-centre-skip footer\{position:sticky;bottom:0/);
  assert.match(css, /\.payment-centre-modal-backdrop[^}]*z-index:220/);
});
