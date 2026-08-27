import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

import {
  PAYMENT_DATE_RANGES,
  buildPaymentCentreQuery,
  defaultPaymentCentreFilters,
  groupPayments,
  paymentAttentionReason,
  paymentAvailableActions,
  paymentNeedsAction,
} from '../src/paymentCentreModel.js';

const paymentCentre = await readFile(new URL('../src/PaymentCentreV112.jsx', import.meta.url), 'utf8');
const app = await readFile(new URL('../src/AppCorrectiveV0174.jsx', import.meta.url), 'utf8');
const css = await readFile(new URL('../src/payment-centre-v112.css', import.meta.url), 'utf8');

test('v1.13 Payment Centre exposes all required date ranges and combined filters', () => {
  assert.deepEqual(PAYMENT_DATE_RANGES.map(([value]) => value), [
    'overdue', 'next_7_days', 'next_30_days', 'next_90_days', 'this_month', 'next_month', 'custom', 'history',
  ]);
  const filters = defaultPaymentCentreFilters();
  const query = buildPaymentCentreQuery({
    ...filters,
    dateRange: 'custom', dateFrom: '2026-08-01', dateTo: '2026-08-31', search: 'ING', status: 'overdue',
    source: 'bill', categoryId: '7', paymentMethod: 'direct_debit', paymentHandling: 'automatic',
    accountId: '2', cardId: '3', requiresAction: true,
  });
  for (const fragment of ['date_range=custom', 'date_from=2026-08-01', 'date_to=2026-08-31', 'search=ING', 'status_filter=overdue', 'source=bill', 'category_id=7', 'payment_method=direct_debit', 'payment_handling=automatic', 'account_id=2', 'card_id=3', 'requires_action=true']) assert.ok(query.includes(fragment));
});

test('attention reasons are explicit and do not rely on colour alone', () => {
  assert.equal(paymentAttentionReason({ status: 'overdue', days_overdue: 4 }), 'Payment is 4 days overdue');
  assert.equal(paymentAttentionReason({ status: 'auto_payment_unconfirmed' }), 'Automatic payment has not been confirmed');
  assert.equal(paymentAttentionReason({ match_review_available: true }), 'Possible transaction match found');
  assert.equal(paymentAttentionReason({ status: 'unknown', expected_amount: null }), 'Payment amount is missing');
  assert.equal(paymentNeedsAction({ status: 'unknown', expected_amount: null }), true);
});

test('valid actions are state and source aware', () => {
  assert.deepEqual(paymentAvailableActions({ source_type: 'bill', status: 'overdue', payment_handling: 'manual' }), ['view', 'mark_paid', 'edit', 'cancel']);
  assert.deepEqual(paymentAvailableActions({ source_type: 'scheduled_payment', status: 'upcoming', recurring_expense_id: 9 }), ['view', 'skip', 'open_recurring']);
  assert.deepEqual(paymentAvailableActions({ source_type: 'bill', status: 'paid' }), ['view']);
  assert.deepEqual(paymentAvailableActions({ source_type: 'scheduled_payment', status: 'auto_payment_unconfirmed', match_review_available: true, recurring_expense_id: 9 }), ['view', 'review', 'skip', 'open_recurring']);
});

test('grouping keeps paid/skipped/cancelled history separate from immediate obligations', () => {
  const groups = Object.fromEntries(groupPayments([
    { id: 1, status: 'overdue', expected_date: '2026-08-20' },
    { id: 2, status: 'paid', expected_date: '2026-08-20' },
    { id: 3, status: 'upcoming', expected_date: '2026-08-27' },
  ], new Date('2026-08-26T00:00:00')));
  assert.equal(groups.Overdue.length, 1);
  assert.equal(groups.History.length, 1);
  assert.equal(groups['Next 7 days'].length, 1);
});

test('Payment Centre closes detail before opening another modal and scopes errors locally', () => {
  assert.match(paymentCentre, /setDetail\(null\); setMarkingPaid\(row\)/);
  assert.match(paymentCentre, /setActionError\(''\)/);
  assert.match(paymentCentre, /payment-centre-action-error/);
  assert.match(paymentCentre, /onMouseDown=\{\(event\) => event\.target === event\.currentTarget && onClose\(\)\}/);
});

test('Payment Centre supports Bill edit/cancel and recurring navigation without duplicate payment storage', () => {
  assert.match(paymentCentre, /onEditBill/);
  assert.match(paymentCentre, /\/bills\/\$\{row\.id\}\/cancel/);
  assert.match(paymentCentre, /onOpenRecurring/);
  assert.doesNotMatch(paymentCentre, /create.*payment.*table/i);
});

test('dashboard uses the unified Payment Centre attention and money-needed summary', () => {
  assert.match(app, /paymentCentreOverview/);
  assert.match(app, /Next 7 days/);
  assert.match(app, /Manual payments/);
  assert.match(app, /Automatic payments/);
  assert.match(app, /View All Payments/);
});

test('mobile Payment Centre prevents horizontal page overflow while preserving scrollable summary cards', () => {
  assert.match(css, /\.payment-centre-page\{[^}]*min-width:0/);
  assert.match(css, /@media\(max-width:620px\)[\s\S]*\.payment-centre-page\{[^}]*overflow-x:hidden/);
  assert.match(css, /@media\(max-width:980px\)[\s\S]*\.payment-centre-summary\{[^}]*display:flex;[^}]*overflow-x:auto/);
  assert.match(css, /max-height:calc\(100dvh/);
});
