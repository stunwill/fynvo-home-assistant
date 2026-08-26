export const PAYMENT_DATE_RANGES = [
  ['overdue', 'Overdue'],
  ['next_7_days', 'Next 7 days'],
  ['next_30_days', 'Next 30 days'],
  ['next_90_days', 'Next 90 days'],
  ['this_month', 'This month'],
  ['next_month', 'Next month'],
  ['custom', 'Custom range'],
  ['history', 'Payment history'],
];

export const PAYMENT_STATUS_LABELS = {
  overdue: 'Overdue',
  due: 'Requires payment',
  due_today: 'Due today',
  upcoming: 'Upcoming',
  expected_automatically: 'Expected automatically',
  auto_payment_unconfirmed: 'Automatic payment not confirmed',
  paid: 'Paid',
  skipped: 'Skipped',
  cancelled: 'Cancelled',
};

export const PAYMENT_METHOD_LABELS = {
  direct_debit: 'Direct Debit',
  automatic_card_payment: 'Automatic Card Payment',
  manual_payment: 'Manual Payment',
  bpay: 'BPAY',
  bank_transfer: 'Bank Transfer',
  cash: 'Cash',
  other: 'Other',
  not_set: 'Not Set',
};

export function paymentStatusLabel(status) {
  return PAYMENT_STATUS_LABELS[status] || String(status || 'Upcoming').replaceAll('_', ' ');
}

export function paymentSourceLabel(row) {
  return row?.source_type === 'bill' ? 'Bill' : 'Recurring Expense';
}

export function paymentNeedsAction(row) {
  return Boolean(row?.requires_action || row?.match_review_available);
}

export function paymentPrimaryAction(row) {
  if (!row || ['paid', 'skipped', 'cancelled'].includes(row.status)) return 'view';
  if (row.match_review_available || row.status === 'auto_payment_unconfirmed') return 'review';
  if (row.payment_handling === 'manual' || ['due', 'due_today', 'overdue'].includes(row.status)) return 'mark_paid';
  return 'view';
}

export function buildPaymentCentreQuery(filters = {}) {
  const params = new URLSearchParams();
  params.set('date_range', filters.dateRange || 'next_30_days');
  if (filters.dateRange === 'custom') {
    if (filters.dateFrom) params.set('date_from', filters.dateFrom);
    if (filters.dateTo) params.set('date_to', filters.dateTo);
  }
  if (filters.search?.trim()) params.set('search', filters.search.trim());
  if (filters.status) params.set('status_filter', filters.status);
  if (filters.source) params.set('source', filters.source);
  if (filters.categoryId) params.set('category_id', filters.categoryId);
  if (filters.paymentMethod) params.set('payment_method', filters.paymentMethod);
  if (filters.paymentHandling) params.set('payment_handling', filters.paymentHandling);
  if (filters.accountId) params.set('account_id', filters.accountId);
  if (filters.cardId) params.set('card_id', filters.cardId);
  if (filters.requiresAction) params.set('requires_action', 'true');
  return `/payment-centre?${params.toString()}`;
}

export function groupPayments(rows = [], todayValue = new Date()) {
  const today = new Date(todayValue);
  today.setHours(0, 0, 0, 0);
  const sevenDays = new Date(today);
  sevenDays.setDate(sevenDays.getDate() + 7);
  const groups = { Overdue: [], Today: [], 'Next 7 days': [], Later: [], History: [] };
  rows.forEach((row) => {
    if (['paid', 'skipped', 'cancelled'].includes(row.status)) {
      groups.History.push(row);
      return;
    }
    if (row.status === 'overdue' || row.status === 'auto_payment_unconfirmed') {
      groups.Overdue.push(row);
      return;
    }
    const raw = row.expected_date || row.due_date;
    if (!raw) {
      groups.Later.push(row);
      return;
    }
    const due = new Date(`${String(raw).slice(0, 10)}T00:00:00`);
    if (due.getTime() === today.getTime()) groups.Today.push(row);
    else if (due > today && due <= sevenDays) groups['Next 7 days'].push(row);
    else groups.Later.push(row);
  });
  return Object.entries(groups).filter(([, values]) => values.length);
}

export function defaultPaymentCentreFilters() {
  return {
    dateRange: 'next_30_days', dateFrom: '', dateTo: '', search: '', status: '', source: '',
    categoryId: '', paymentMethod: '', paymentHandling: '', accountId: '', cardId: '', requiresAction: false,
  };
}
