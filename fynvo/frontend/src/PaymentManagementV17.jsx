import { useEffect, useMemo, useState } from 'react';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

const methodLabels = {
  direct_debit: 'Direct Debit', automatic_card_payment: 'Automatic Card Payment', bpay: 'BPAY', bank_transfer: 'Bank Transfer',
  manual_payment: 'Manual Payment', cash: 'Cash', other: 'Other', not_set: 'Not Set',
};
const statusLabels = {
  upcoming: 'Upcoming', due: 'Requires payment', overdue: 'Overdue', expected_automatically: 'Expected automatically',
  auto_payment_unconfirmed: 'Automatic payment not confirmed', paid: 'Paid', skipped: 'Skipped', cancelled: 'Cancelled',
};

export function recurringV17Values(row = {}) {
  const method = row.payment_method || (row.direct_debit ? 'direct_debit' : 'not_set');
  return {
    name: row.name || '', amount: row.amount || '', frequency: row.frequency || 'monthly', next_due_date: String(row.next_due_date || '').slice(0, 10),
    payment_handling: row.payment_handling || (['direct_debit', 'automatic_card_payment'].includes(method) ? 'automatic' : 'manual'),
    payment_method: method, account_id: row.account_id || '', card_id: row.card_id || '', category: row.category || '', category_id: row.category_id || '',
    expense_type: row.expense_type || '', expense_type_id: row.expense_type_id || '', payee_merchant: row.payee_merchant || '',
    amount_type: row.amount_type || (row.variable_amount ? 'variable_estimated' : 'fixed'), auto_payment_grace_days: row.auto_payment_grace_days ?? 3,
    notes: row.notes || '', is_active: row.is_active ?? true, effective_from: '',
  };
}

export function RecurringPaymentFieldsV17({ values, set, data }) {
  const method = values.payment_method || 'not_set';
  const selectedCard = (data.cards || []).find((card) => Number(card.id) === Number(values.card_id));
  const activeCards = (data.cards || []).filter((card) => card.is_active !== false);
  const setHandling = (handling) => {
    set('payment_handling', handling);
    if (handling === 'automatic' && !['direct_debit', 'automatic_card_payment', 'other'].includes(method)) set('payment_method', 'direct_debit');
    if (handling === 'manual' && ['direct_debit', 'automatic_card_payment'].includes(method)) set('payment_method', 'bpay');
  };
  const setMethod = (next) => {
    set('payment_method', next);
    if (next === 'direct_debit') { set('payment_handling', 'automatic'); set('card_id', ''); }
    else if (next === 'automatic_card_payment') { set('payment_handling', 'automatic'); set('account_id', ''); }
    else if (next !== 'other') { set('payment_handling', 'manual'); set('account_id', ''); set('card_id', ''); }
  };
  return <fieldset className="payment-v17-section"><legend>Payment</legend>
    <span className="payment-v17-question">How is this normally paid?</span>
    <div className="payment-v17-handling" role="radiogroup" aria-label="How is this expense normally paid?">
      <button type="button" role="radio" aria-checked={values.payment_handling === 'automatic'} className={values.payment_handling === 'automatic' ? 'active' : ''} onClick={() => setHandling('automatic')}>Paid automatically</button>
      <button type="button" role="radio" aria-checked={values.payment_handling === 'manual'} className={values.payment_handling === 'manual' ? 'active' : ''} onClick={() => setHandling('manual')}>I pay this manually</button>
    </div>
    <label className="field"><span>Payment Method</span><select value={method} onChange={(event) => setMethod(event.target.value)}>{Object.entries(methodLabels).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
    {method === 'direct_debit' && <label className="field"><span>Bank Account</span><select required value={values.account_id || ''} onChange={(event) => set('account_id', event.target.value)}><option value="">Choose bank account</option>{(data.accounts || []).filter((account) => account.is_active !== false).map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>}
    {method === 'automatic_card_payment' && <div className="payment-v17-card-field"><label className="field"><span>Card</span><select required value={values.card_id || ''} onChange={(event) => set('card_id', event.target.value)}><option value="">{activeCards.length ? 'Choose Card' : 'No Cards available'}</option>{activeCards.map((card) => <option key={card.id} value={card.id}>{card.display_name}</option>)}</select></label>{selectedCard && <small className="payment-v17-linked">Linked to account: <strong>{selectedCard.account_name}</strong></small>}{!activeCards.length && <small className="payment-v17-linked">Add a Card from Accounts → Cards, then return to this expense.</small>}</div>}
    {values.payment_handling === 'automatic' && <label className="field"><span>Confirmation grace period</span><select value={values.auto_payment_grace_days ?? 3} onChange={(event) => set('auto_payment_grace_days', Number(event.target.value))}><option value={1}>1 day</option><option value={2}>2 days</option><option value={3}>3 days</option><option value={5}>5 days</option><option value={7}>7 days</option></select></label>}
  </fieldset>;
}

export function CardsPageV17({ accounts, cards, onRefresh }) {
  const [edit, setEdit] = useState(null); const [error, setError] = useState('');
  const activeAccounts = accounts.filter((account) => account.is_active !== false && !account.archived_at);
  const start = (card = null, accountId = '') => setEdit({ id: card?.id || null, name: card?.name || '', account_id: card?.account_id || accountId || activeAccounts[0]?.id || '', card_type: card?.card_type || 'debit', last_four: card?.last_four || '', is_active: card?.is_active ?? true });
  const save = async (event) => { event.preventDefault(); setError(''); const response = await api(edit.id ? `/cards/${edit.id}` : '/cards', { method: edit.id ? 'PUT' : 'POST', body: JSON.stringify(edit) }); if (!response.ok) { const payload = await response.json().catch(() => null); setError(payload?.detail || 'Could not save Card.'); return; } setEdit(null); await onRefresh(); };
  const grouped = useMemo(() => accounts.map((account) => ({ account, cards: cards.filter((card) => Number(card.account_id) === Number(account.id)) })), [accounts, cards]);
  return <section className="panel cards-v17-page"><div className="panel-head"><div><h2>Cards</h2><p className="muted">Cards belong to an Account. Fynvo stores only the last four digits.</p></div><button className="primary ghost" disabled={!activeAccounts.length} onClick={() => start()}>+ Add Card</button></div>
    <div className="cards-v17-groups">{grouped.map(({ account, cards: accountCards }) => <article key={account.id} className="cards-v17-account"><div><strong>{account.name}</strong><small>{account.institution || account.account_type}</small></div><div className="cards-v17-list">{accountCards.length ? accountCards.map((card) => <button key={card.id} type="button" className="cards-v17-card" onClick={() => start(card)}><span><strong>{card.display_name}</strong><small>{card.card_type} · {card.is_active ? 'Active' : 'Inactive'}</small></span><small>Linked account: {card.account_name}</small></button>) : <p className="muted">No Cards linked to this Account.</p>}{account.is_active !== false && !account.archived_at && <button type="button" className="link-button" onClick={() => start(null, account.id)}>+ Add Card</button>}</div></article>)}</div>
    {edit && <div className="modal-backdrop"><form className="modal" onSubmit={save}><div className="panel-head"><h2>{edit.id ? 'Edit Card' : 'Add Card'}</h2><button type="button" onClick={() => setEdit(null)}>×</button></div><div className="form-grid"><label className="field"><span>Card Name</span><input required value={edit.name} onChange={(event) => setEdit({ ...edit, name: event.target.value })}/></label><label className="field"><span>Linked Account</span><select required value={edit.account_id} onChange={(event) => setEdit({ ...edit, account_id: event.target.value })}>{activeAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label><label className="field"><span>Card Type</span><select value={edit.card_type} onChange={(event) => setEdit({ ...edit, card_type: event.target.value })}><option value="debit">Debit</option><option value="credit">Credit</option><option value="prepaid">Prepaid</option><option value="other">Other</option></select></label><label className="field"><span>Last 4 Digits</span><input required inputMode="numeric" pattern="[0-9]{4}" maxLength="4" value={edit.last_four} onChange={(event) => setEdit({ ...edit, last_four: event.target.value.replace(/\D/g, '').slice(0, 4) })}/></label>{edit.id && <label className="field checkbox"><input type="checkbox" checked={edit.is_active} onChange={(event) => setEdit({ ...edit, is_active: event.target.checked })}/><span>Active</span></label>}</div>{error && <p className="error">{error}</p>}<div className="modal-actions"><button type="button" onClick={() => setEdit(null)}>Cancel</button><button className="primary">Save Card</button></div></form></div>}
  </section>;
}

function PaymentStatusBadge({ status }) { return <span className={`payment-v17-status status-${status}`}>{statusLabels[status] || status}</span>; }

export function PaymentsAttentionV17({ rows, money, dateLabel, onRefresh }) {
  const [paying, setPaying] = useState(null); const [reviewing, setReviewing] = useState(null);
  const [form, setForm] = useState({ paid_date: new Date().toISOString().slice(0, 10), paid_amount: '', note: '' });
  const markPaid = async (event) => { event.preventDefault(); const response = await api(`/scheduled-payments/${paying.id}/mark-paid`, { method: 'POST', body: JSON.stringify({ ...form, paid_amount: form.paid_amount || paying.expected_amount }) }); if (response.ok) { setPaying(null); await onRefresh(); } };
  const skip = async () => { if (!paying) return; const response = await api(`/scheduled-payments/${paying.id}/skip`, { method: 'POST', body: JSON.stringify({ note: form.note || 'Skipped by user' }) }); if (response.ok) { setPaying(null); await onRefresh(); } };
  return <article className="panel payments-v17-attention"><div className="panel-head compact"><div><h2>Payments requiring attention</h2><small>{rows.length ? `${rows.length} payment${rows.length === 1 ? '' : 's'} need review` : 'Nothing needs attention'}</small></div></div>{rows.length ? rows.slice(0, 6).map((row) => <div className="payments-v17-row" key={row.id}><div><PaymentStatusBadge status={row.status}/><strong>{row.name}</strong><small>{row.payment_method_label}{row.account_name ? ` · ${row.account_name}` : ''}</small></div><div><strong>{money(row.expected_amount) || 'Not set'}</strong><small>{dateLabel(row.expected_date)}</small></div>{row.payment_handling === 'manual' ? <button onClick={() => { setPaying(row); setForm({ paid_date: new Date().toISOString().slice(0, 10), paid_amount: row.expected_amount || '', note: '' }); }}>Mark paid</button> : <button type="button" onClick={() => setReviewing(row)}>Review</button>}</div>) : <p className="muted">No overdue, due or unconfirmed automatic payments.</p>}
    {paying && <div className="modal-backdrop"><form className="modal" onSubmit={markPaid}><div className="panel-head"><div><h2>Mark as paid</h2><p>{paying.name} · {money(paying.expected_amount)}</p></div><button type="button" onClick={() => setPaying(null)}>×</button></div><div className="form-grid"><label className="field"><span>Paid date</span><input type="date" value={form.paid_date} onChange={(event) => setForm({ ...form, paid_date: event.target.value })}/></label><label className="field"><span>Paid amount</span><input value={form.paid_amount} onChange={(event) => setForm({ ...form, paid_amount: event.target.value })}/></label><label className="field wide"><span>Note (optional)</span><input value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })}/></label></div><p className="muted">If this payment did not occur, use Skip payment instead of recording a $0 payment.</p><div className="modal-actions"><button type="button" className="danger-ghost" onClick={skip}>Skip payment</button><button type="button" onClick={() => setPaying(null)}>Cancel</button><button className="primary">Mark as paid</button></div></form></div>}
    {reviewing && <div className="modal-backdrop"><section className="modal"><div className="panel-head"><div><h2>Automatic payment not confirmed</h2><p>{reviewing.name}</p></div><button type="button" onClick={() => setReviewing(null)}>×</button></div><div className="detail-grid"><div className="detail-item"><span>Expected amount</span><strong>{money(reviewing.expected_amount)}</strong></div><div className="detail-item"><span>Expected date</span><strong>{dateLabel(reviewing.expected_date)}</strong></div><div className="detail-item"><span>Payment Method</span><strong>{reviewing.payment_method_label}</strong></div><div className="detail-item"><span>Payment source</span><strong>{reviewing.card_name || reviewing.account_name || 'Not set'}</strong></div></div><p className="muted">Review CSV Import or the Review Queue to confirm a matching bank transaction. Fynvo will not mark this payment paid without confirmation.</p><div className="modal-actions"><button type="button" onClick={() => setReviewing(null)}>Close</button></div></section></div>}
  </article>;
}

export function PaymentReconciliationV17({ money, dateLabel }) {
  const [rows, setRows] = useState([]); const [tolerance, setTolerance] = useState(7);
  const load = () => api(`/payments/match-candidates?date_tolerance_days=${tolerance}`).then(async (response) => setRows(response.ok ? await response.json() : []));
  useEffect(() => { load(); }, [tolerance]);
  const confirm = async (row) => { const response = await api(`/scheduled-payments/${row.scheduled_payment_id}/match`, { method: 'POST', body: JSON.stringify({ transaction_id: row.transaction_id, confidence: row.confidence }) }); if (response.ok) load(); };
  const reject = async (row) => { const response = await api(`/scheduled-payments/${row.scheduled_payment_id}/reject-match`, { method: 'POST', body: JSON.stringify({ transaction_id: row.transaction_id }) }); if (response.ok) load(); };
  const ignore = async (row) => { const response = await api(`/payments/transactions/${row.transaction_id}/ignore`, { method: 'POST' }); if (response.ok) load(); };
  return <section className="panel payments-v17-review"><div className="panel-head"><div><h2>Scheduled Payment Review</h2><p className="muted">Review imported transactions that may match expected recurring payments.</p></div><label className="select-shell">Date tolerance<select value={tolerance} onChange={(event) => setTolerance(Number(event.target.value))}><option value={2}>±2 days</option><option value={4}>±4 days</option><option value={7}>±7 days</option><option value={14}>±14 days</option></select></label></div>{rows.length ? <div className="table"><div className="thead"><span>Imported transaction</span><span>Possible match</span><span>Confidence</span><span>Difference</span><span></span></div>{rows.map((row) => <div className="tr" key={`${row.transaction_id}-${row.scheduled_payment_id}`}><span>{row.transaction_description}<small>{dateLabel(row.transaction_date)} · {money(row.transaction_amount)}</small></span><span>{row.expense_name}<small>Expected {dateLabel(row.expected_date)} · {money(row.expected_amount)}</small>{row.learned_mapping && <small>Previously confirmed merchant mapping</small>}</span><span><span className={`payment-v17-confidence ${row.confidence}`}>{row.confidence}</span></span><span>{money(row.difference)}</span><div className="payment-v17-match-actions"><button type="button" className="primary ghost" onClick={() => confirm(row)}>Confirm match</button><button type="button" onClick={() => reject(row)}>Not this expense</button><button type="button" onClick={() => ignore(row)}>Ignore transaction</button></div></div>)}</div> : <p className="muted">No suggested scheduled-payment matches currently need review.</p>}</section>;
}
