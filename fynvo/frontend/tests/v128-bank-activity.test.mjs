import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), 'utf8');
const [activity, review, css, shell] = await Promise.all([
  read('src/TransactionWorkspaceCore.jsx'), read('src/PaymentManagementV17.jsx'),
  read('src/bank-activity-v128.css'), read('src/main.jsx'),
]);

test('Activity retains protected primary loading and ingress-safe APIs while adding review', () => {
  assert.match(activity, /payments\/transactions\?limit=2000/);
  assert.match(activity, /payments\/match-candidates/);
  assert.match(activity, /filters\.reconciliation === 'review'/);
  assert.match(activity, /option value="pending">Pending/);
  assert.match(activity, /category_suggestion/);
  assert.match(activity, /provider_category/);
  assert.match(activity, /Confirm match/);
  assert.match(activity, /Not this payment/);
});

test('Review Queue uses deterministic strong candidate IDs with confirmation and rejection', () => {
  assert.match(review, /row\.review_id/);
  assert.match(review, /row\.evidence\.map/);
  assert.match(review, /reject-match/);
  assert.match(review, /Confirm match/);
  assert.match(review, /role="alert"/);
  assert.match(review, /role="status"/);
});

test('narrow ingress review controls and transaction detail are contained', () => {
  assert.match(css, /max-width: 420px/);
  assert.match(css, /min-height: 44px/);
  assert.match(css, /100dvh/);
  assert.match(css, /overflow-wrap: anywhere/);
  assert.match(shell, /bank-activity-v128\.css/);
});
