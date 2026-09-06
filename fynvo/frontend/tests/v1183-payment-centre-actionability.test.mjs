import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const payment = await read('src/PaymentCentreMobileV1183.jsx');
const wrapper = await read('src/AppCorrectiveV1163.jsx');
const css = await read('src/payment-centre-mobile-v1183.css');
const main = await read('src/main.jsx');
const shell = await read('src/AppV13.jsx');
const config = await read('../config.yaml');
const backendConfig = await read('../backend/app/config.py');
const packageJson = JSON.parse(await read('package.json'));

test('v1.18.3 mobile Payment Centre is mounted without replacing desktop Payment Centre', () => {
  assert.match(wrapper, /PaymentCentreMobileV1183/);
  assert.match(wrapper, /max-width: 980px/);
  assert.match(wrapper, /payment-v1183-overlay/);
  assert.match(css, /body\.fynvo-payment-centre-page \.payment-v1182-shell\{display:none!important\}/);
  assert.match(css, /@media\(min-width:981px\)/);
  assert.match(main, /payment-centre-mobile-v1183\.css/);
});

test('status navigation exposes authoritative counts and monetary summary', () => {
  assert.match(payment, /Next 30 days · \{summary\.next30\?\.count/);
  assert.match(payment, /Overdue · \{summary\.overdue\?\.count/);
  assert.match(payment, /Needs attention · \{summary\.attention\?\.count/);
  assert.match(payment, /Payment Centre summary/);
  assert.match(payment, /summary\.overdue\.total/);
  assert.match(payment, /before_next_income\?\.commitments_total/);
  assert.match(payment, /summary\.next30\.total/);
});

test('before-pay unavailable state is actionable and keeps authoritative calculation detail', () => {
  assert.match(payment, /Cash position needs setup/);
  assert.match(payment, /Fix setup/);
  assert.match(payment, /Review Income/);
  for (const label of ['Available now', 'Required before pay', 'Next income', 'View calculation', 'Projected before pay', 'Projected after pay']) assert.match(payment, new RegExp(label));
  assert.match(payment, /planning\?\.pay_cycle/);
  assert.doesNotMatch(payment, /apiRequest\('\/payment-planning\/pay-cycle'\)/);
});

test('missing information names real fields and opens a resolution path', () => {
  assert.match(payment, /Missing information/);
  assert.match(payment, /Due date/);
  assert.match(payment, /Payment method/);
  assert.match(payment, /Funding account/);
  assert.match(payment, /Category/);
  assert.match(payment, /Fix details/);
});

test('payment cards reduce action weight and distinguish automatic state', () => {
  assert.match(payment, /payment-v1183-card-name/);
  assert.match(payment, /payment-v1183-card-amount/);
  assert.match(payment, /Expected automatically/);
  assert.match(payment, /Automatic payment unconfirmed/);
  assert.match(payment, /payment_handling === 'automatic'/);
  assert.match(css, /payment-v1183-card-actions/);
  assert.match(css, /grid-template-columns:minmax\(0,1fr\) 48px/);
});

test('grouped mode is collapsible and planning oriented without duplicate buckets', () => {
  for (const label of ['Overdue', 'Due before next pay', 'Next 7 days', 'Later this month']) assert.match(payment, new RegExp(label));
  assert.match(payment, /aria-expanded=!/);
  assert.match(payment, /group\.total/);
  assert.match(payment, /timelineMode\.v1183/);
});

test('bulk Mark paid reuses authoritative lifecycle endpoints with confirmation', () => {
  assert.match(payment, /Select all/);
  assert.match(payment, /window\.confirm/);
  assert.match(payment, /Bulk marked paid/);
  assert.match(payment, /\/bills\/\$\{row\.id\}\/mark-paid/);
  assert.match(payment, /\/scheduled-payments\/\$\{row\.id\}\/mark-paid/);
});

test('bulk Skip reuses v1.15 lifecycle endpoint and preserves version checks', () => {
  assert.match(payment, /\/scheduled-payments\/\$\{row\.id\}\/skip/);
  assert.match(payment, /reason: 'User requested skip'/);
  assert.match(payment, /version: row\.version/);
  assert.match(payment, /matched_transaction_id/);
  assert.match(payment, /Bulk skipped from Payment Centre/);
});

test('mobile layout protects safe areas, touch targets, narrow iPhones and reduced motion', () => {
  assert.match(css, /safe-area-inset-bottom/);
  assert.match(css, /min-height:44px/);
  assert.match(css, /@media\(max-width:430px\)/);
  assert.match(css, /@media\(max-width:393px\)/);
  assert.match(css, /@media\(max-width:374px\)/);
  assert.match(css, /@media\(max-width:329px\)/);
  assert.match(css, /prefers-reduced-motion:reduce/);
  assert.match(css, /\.modal \.modal-actions\{position:sticky/);
});

test('wrapper avoids the v1.17.6 self-triggering observer regression', () => {
  assert.match(wrapper, /currentMount === nextMount \? currentMount : nextMount/);
  assert.match(wrapper, /useEffect\(\(\) => \{ if \(paymentMount\) refreshPaymentSupporting\(\); \}, \[paymentMount, authState\?\.authenticated\]\)/);
  assert.doesNotMatch(wrapper, /if \(paymentActive\) refreshPaymentSupporting\(\)/);
});

test('release metadata is aligned to v1.18.3', () => {
  assert.match(config, /version: "1\.18\.3"/);
  assert.equal(packageJson.version, '1.18.3');
  assert.match(backendConfig, /APP_VERSION = "1\.18\.3"/);
  assert.match(shell, /PRODUCTION_VERSION = '1\.18\.3'/);
});
