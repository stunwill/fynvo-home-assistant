import { useEffect, useMemo, useState } from 'react';
import AccountsCardsPageV1163 from './AccountsCardsPageV1163.jsx';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

const cardDefaults = (card = null, accounts = []) => ({
  id: card?.id || null,
  name: card?.name || '',
  account_id: card?.account_id || accounts[0]?.id || '',
  card_type: card?.card_type || 'debit',
  last_four: card?.last_four || '',
  is_active: card?.is_active ?? true,
});

export default function AccountsCardsWorkspaceV1163({ activeAccounts, cards, initialView, onEditAccount, onAddAccount, onRefresh }) {
  const [accounts, setAccounts] = useState(activeAccounts);
  const [localCards, setLocalCards] = useState(cards);
  const [cardEdit, setCardEdit] = useState(null);
  const [manage, setManage] = useState(null);
  const [dependencies, setDependencies] = useState(null);
  const [destination, setDestination] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const selectableAccounts = useMemo(() => accounts.filter((account) => account.is_active !== false && !account.archived_at), [accounts]);

  async function refreshLocal() {
    const [accountResponse, cardResponse] = await Promise.all([api('/accounts?include_archived=true'), api('/cards?include_inactive=true')]);
    if (accountResponse.ok) setAccounts(await accountResponse.json());
    if (cardResponse.ok) setLocalCards(await cardResponse.json());
    await onRefresh?.();
  }

  useEffect(() => { setLocalCards(cards); }, [cards]);
  useEffect(() => {
    let cancelled = false;
    api('/accounts?include_archived=true').then(async (response) => {
      if (!cancelled && response.ok) setAccounts(await response.json());
    });
    return () => { cancelled = true; };
  }, [activeAccounts]);

  const startManage = async (account) => {
    setManage(account);
    setDependencies(null);
    setDestination('');
    setError('');
    const response = await api(`/accounts/${account.id}/dependencies`);
    if (response.ok) setDependencies(await response.json());
    else setError('Could not inspect this Account yet.');
  };

  const editAccountDetails = () => {
    const account = manage;
    setManage(null);
    if (account) onEditAccount(account);
  };

  const archiveOnly = async () => {
    setBusy(true); setError('');
    const response = await api(`/accounts/${manage.id}/archive`, { method: 'POST' });
    if (response.ok) { setManage(null); await refreshLocal(); } else setError((await response.json().catch(() => null))?.detail || 'Could not archive Account.');
    setBusy(false);
  };

  const restore = async () => {
    setBusy(true); setError('');
    const response = await api(`/accounts/${manage.id}/restore`, { method: 'POST' });
    if (response.ok) { setManage(null); await refreshLocal(); } else setError((await response.json().catch(() => null))?.detail || 'Could not restore Account.');
    setBusy(false);
  };

  const moveAndArchive = async () => {
    if (!destination) { setError('Choose the Account that should receive eligible records.'); return; }
    setBusy(true); setError('');
    const response = await api(`/accounts/${manage.id}/move-and-archive`, { method: 'POST', body: JSON.stringify({ destination_account_id: Number(destination) }) });
    if (response.ok) { setManage(null); await refreshLocal(); } else setError((await response.json().catch(() => null))?.detail || 'Could not move records and archive Account.');
    setBusy(false);
  };

  const permanentlyDelete = async () => {
    setBusy(true); setError('');
    const response = await api(`/accounts/${manage.id}`, { method: 'DELETE' });
    if (response.ok) { setManage(null); await refreshLocal(); } else setError((await response.json().catch(() => null))?.detail || 'This Account cannot be permanently deleted.');
    setBusy(false);
  };

  const saveCard = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    const payload = { ...cardEdit, account_id: Number(cardEdit.account_id) };
    const response = await api(cardEdit.id ? `/cards/${cardEdit.id}` : '/cards', { method: cardEdit.id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
    if (response.ok) { setCardEdit(null); await refreshLocal(); } else setError((await response.json().catch(() => null))?.detail || 'Could not save Card.');
    setBusy(false);
  };

  return <>
    <AccountsCardsPageV1163
      accounts={accounts}
      cards={localCards}
      initialView={initialView}
      onEditAccount={startManage}
      onAddAccount={onAddAccount}
      onEditCard={(card) => setCardEdit(cardDefaults(card, selectableAccounts))}
      onAddCard={() => setCardEdit(cardDefaults(null, selectableAccounts))}
    />

    {manage && <div className="modal-backdrop"><section className="modal account-manage-v1163" role="dialog" aria-modal="true" aria-labelledby="account-manage-title">
      <div className="panel-head"><div><h2 id="account-manage-title">Manage {manage.name}</h2><p className="muted">Edit, archive, consolidate or restore this Account without silently changing financial history.</p></div><button type="button" onClick={() => setManage(null)} aria-label="Close Account management">×</button></div>
      {dependencies ? <div className="account-dependency-list"><h3>Account dependencies</h3>{dependencies.dependencies.filter((item) => item.count).length ? dependencies.dependencies.filter((item) => item.count).map((item) => <div className="list-row" key={item.type}><span>{item.label}<small>{item.classification === 'historical' ? 'Historical, preserved' : item.action === 'move' ? 'Eligible to move where safe' : 'Future configuration can move'}</small></span><strong>{item.count}</strong></div>) : <p className="muted">No dependent records were found.</p>}{dependencies.warnings?.map((warning) => <p className="notice" key={warning}>{warning}</p>)}</div> : <p className="muted" role="status">Checking dependencies…</p>}
      {manage.archived_at || manage.is_active === false ? <div className="modal-actions"><button type="button" onClick={() => setManage(null)}>Cancel</button><button type="button" className="primary ghost" onClick={editAccountDetails}>Edit Account details</button><button type="button" className="primary" disabled={busy} onClick={restore}>{busy ? 'Working…' : 'Restore Account'}</button>{dependencies?.can_delete && <button type="button" className="danger-action" disabled={busy} onClick={permanentlyDelete}>Delete permanently</button>}</div> : <>
        <div className="account-management-choice"><h3>Account details</h3><p className="muted">Update the Account name, institution, type and other supported details.</p><button type="button" className="primary ghost" onClick={editAccountDetails}>Edit Account details</button></div>
        <div className="account-management-choice"><h3>Archive only</h3><p className="muted">Safest option. Existing Transactions, Scheduled Payments and history remain linked to this Account.</p><button type="button" disabled={busy} onClick={archiveOnly}>Archive Account</button></div>
        <div className="account-management-choice"><h3>Move eligible records &amp; archive</h3><p className="muted">Moves eligible records to an active Account while preserving historical Scheduled Payments, Transfers and protected Transactions.</p><label className="field"><span>Move eligible records to</span><select value={destination} onChange={(event) => setDestination(event.target.value)}><option value="">Choose Account</option>{selectableAccounts.filter((account) => Number(account.id) !== Number(manage.id)).map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label><button type="button" className="primary" disabled={busy || !destination || dependencies?.move_blocked} onClick={moveAndArchive}>{busy ? 'Working…' : 'Move records & archive'}</button>{dependencies?.move_blocked && <p className="muted">Move &amp; Archive is blocked for this Account because moving its Transactions would change balance semantics. Archive Only remains available.</p>}</div>
        {dependencies?.can_delete && <div className="account-management-choice danger-zone"><h3>Danger zone</h3><p className="muted">This Account has no dependencies and may be permanently deleted.</p><button type="button" className="danger-action" disabled={busy} onClick={permanentlyDelete}>Delete permanently</button></div>}
        <div className="modal-actions"><button type="button" onClick={() => setManage(null)}>Close</button></div>
      </>}
      {error && <p className="error banner" role="alert">{error}</p>}
    </section></div>}

    {cardEdit && <div className="modal-backdrop"><form className="modal" onSubmit={saveCard}><div className="panel-head"><h2>{cardEdit.id ? 'Edit Card' : 'Add Card'}</h2><button type="button" onClick={() => setCardEdit(null)} aria-label="Close Card editor">×</button></div><div className="form-grid"><label className="field"><span>Card Name</span><input required value={cardEdit.name} onChange={(event) => setCardEdit({ ...cardEdit, name: event.target.value })}/></label><label className="field"><span>Linked Account</span><select required value={cardEdit.account_id} onChange={(event) => setCardEdit({ ...cardEdit, account_id: event.target.value })}><option value="">Choose Account</option>{selectableAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label><label className="field"><span>Card Type</span><select value={cardEdit.card_type} onChange={(event) => setCardEdit({ ...cardEdit, card_type: event.target.value })}><option value="debit">Debit</option><option value="credit">Credit</option><option value="prepaid">Prepaid</option><option value="other">Other</option></select></label><label className="field"><span>Last 4 Digits</span><input required inputMode="numeric" pattern="[0-9]{4}" maxLength="4" value={cardEdit.last_four} onChange={(event) => setCardEdit({ ...cardEdit, last_four: event.target.value.replace(/\D/g, '').slice(0, 4) })}/></label>{cardEdit.id && <label className="field checkbox"><input type="checkbox" checked={cardEdit.is_active} onChange={(event) => setCardEdit({ ...cardEdit, is_active: event.target.checked })}/><span>Active</span></label>}</div>{error && <p className="error" role="alert">{error}</p>}<div className="modal-actions"><button type="button" onClick={() => setCardEdit(null)}>Cancel</button><button type="submit" className="primary" disabled={busy || selectableAccounts.length === 0}>{busy ? 'Saving…' : 'Save Card'}</button></div>{selectableAccounts.length === 0 && <p className="muted">Add or restore an active Account before adding a Card.</p>}</form></div>}
  </>;
}
