import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const payment = fs.readFileSync(new URL('../src/PaymentManagementV17.jsx', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../src/v191.css', import.meta.url), 'utf8');
const main = fs.readFileSync(new URL('../src/main.jsx', import.meta.url), 'utf8');

test('Payment Method changes are a single state transition', () => {
  const block = payment.slice(payment.indexOf('const setMethod'), payment.indexOf('return <fieldset'));
  assert.match(block, /set\('payment_method', next\)/);
  assert.doesNotMatch(block, /set\('card_id'/);
  assert.doesNotMatch(block, /set\('account_id'/);
});

test('conditional payment source fields remain wired to selected method', () => {
  assert.match(payment, /method === 'direct_debit'/);
  assert.match(payment, /method === 'automatic_card_payment'/);
  assert.match(payment, /Linked to account:/);
});

test('recurring editor is constrained below the fixed mobile app bar', () => {
  assert.match(css, /\.modal-backdrop:has\(form\.modal \.payment-v17-section\)/);
  assert.match(css, /top: 64px/);
  assert.match(css, /max-height: calc\(100dvh - 64px/);
  assert.match(css, /overflow-x: hidden/);
  assert.match(css, /overflow-y: auto/);
});

test('recurring modal header and actions stay accessible while body scrolls', () => {
  assert.match(css, /> \.panel-head \{/);
  assert.match(css, /position: sticky/);
  assert.match(css, /> \.modal-actions \{/);
  assert.match(css, /grid-template-columns: minmax\(0, 1fr\) minmax\(0, 1fr\)/);
});

test('v1.9.1 correction stylesheet is loaded last', () => {
  assert.match(main, /import '\.\/v191\.css';/);
  assert.ok(main.lastIndexOf("./v191.css") > main.lastIndexOf("./payment-v17.css"));
});
