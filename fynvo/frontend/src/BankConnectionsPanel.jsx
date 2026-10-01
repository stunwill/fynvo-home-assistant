import { useEffect, useMemo, useRef, useState } from 'react';
import { apiRequest } from './apiClient.js';
import './bank-connections-v126.css';

const errorText = (error) => error?.message || 'Bank connection could not be updated.';
const money = (value) => value == null ? 'Balance unavailable' : new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(Number(value));
const freshness = (value) => {
  if (!value) return 'Never synced';
  const time = new Date(value).getTime();
  if (!Number.isFinite(time)) return 'Sync time unavailable';
  const minutes = Math.max(0, Math.round((Date.now() - time) / 60000));
  return minutes < 2 ? 'Updated just now' : minutes < 60 ? `Updated ${minutes} min ago` : `Updated ${Math.round(minutes / 60)} hr ago`;
};
const eligible = (account) => account.is_active !== false && !account.archived_at && ['transaction', 'savings', 'offset', 'credit_card', 'mortgage', 'personal_loan', 'car_loan', 'line_of_credit'].includes(account.account_type);
const comparable = (value) => String(value || '').trim().toLocaleLowerCase('en-AU').replace(/\s+/g, ' ');
const suggested = (bank, account) => comparable(bank.name) === comparable(account.name) && comparable(bank.institution_name) === comparable(account.institution) && bank.account_type === account.account_type;

export default function BankConnectionsPanel({ onClose, targetExternalAccountId = null }) {
  const [state, setState] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [apiKey, setApiKey] = useState('');
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [setup, setSetup] = useState(null);
  const [choice, setChoice] = useState('link');
  const [accountId, setAccountId] = useState('');
  const [name, setName] = useState('');
  const [accountType, setAccountType] = useState('transaction');
  const dialog = useRef(null);
  const trigger = useRef(null);
  const backButton = useRef(null);

  const load = async () => {
    try {
      const [banking, fynvoAccounts] = await Promise.all([apiRequest('/bank-connections/redbark/status'), apiRequest('/accounts')]);
      setState(banking);
      setAccounts(Array.isArray(fynvoAccounts) ? fynvoAccounts : []);
    } catch (failure) { setError(errorText(failure)); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (setup) dialog.current?.focus();
    else (trigger.current?.isConnected ? trigger.current : backButton.current)?.focus();
  }, [setup]);
  const externalRows = useMemo(() => (state?.connections || []).flatMap((connection) => (connection.accounts || []).map((account) => ({ ...account, connection }))), [state]);
  const linkedIds = new Set(externalRows.filter((item) => item.fynvo_account_id).map((item) => Number(item.fynvo_account_id)));
  const candidates = accounts.filter((item) => eligible(item) && !linkedIds.has(Number(item.id)));
  const sortedCandidates = setup ? [...candidates].sort((a, b) => Number(suggested(setup, b)) - Number(suggested(setup, a))) : candidates;
  const activeConnections = (state?.connections || []).filter((connection) => connection.status !== 'disconnected');
  const connectedCount = externalRows.filter((item) => item.state === 'connected' && item.connection.status !== 'disconnected').length;
  const setupCount = externalRows.filter((item) => item.state === 'unresolved' && item.connection.status !== 'disconnected').length;
  const attentionCount = state?.required_actions?.filter((item) => item.state === 'needs_attention').length || 0;
  const providerState = !state?.configured ? 'Setup required' : !(state.connections || []).length ? 'No connections' : !activeConnections.length ? 'Disconnected' : attentionCount ? 'Needs attention' : 'Connected';
  useEffect(() => {
    if (!targetExternalAccountId || !state) return;
    const item = externalRows.find((row) => Number(row.id) === Number(targetExternalAccountId) && row.state === 'unresolved' && row.connection.status !== 'disconnected');
    if (item) { setSetup(item); setChoice('link'); setAccountId(''); setName(item.name || ''); setAccountType(item.account_type || 'transaction'); }
  }, [targetExternalAccountId, state]);
  const groups = [
    ['needs_attention', 'Needs attention'], ['unresolved', 'Needs setup'], ['connected', 'Connected accounts'], ['ignored', 'Ignored accounts'],
  ];

  const execute = async (key, request, success) => {
    setBusy(key); setError(''); setMessage('');
    try {
      await request();
      await load();
      if (success) setMessage(success);
      window.dispatchEvent(new CustomEvent('fynvo:balances-updated'));
      return true;
    } catch (failure) { setError(errorText(failure)); return false; }
    finally { setBusy(''); }
  };
  const mapping = async (item, payload) => {
    const saved = await execute(`map:${item.id}`, () => apiRequest(`/bank-connections/${item.connection.id}/accounts/${item.id}/mapping`, { method: 'POST', body: JSON.stringify(payload) }), 'Bank account updated.');
    if (saved && ['link', 'create'].includes(payload.action)) await sync(item.connection);
    return saved;
  };
  const begin = (item, event, initialChoice = 'link') => {
    trigger.current = event.currentTarget;
    setError(''); setSetup(item); setChoice(initialChoice); setAccountId(''); setName(item.name || ''); setAccountType(item.account_type || 'transaction');
  };
  const closeSetup = () => setSetup(null);
  const confirm = async (event) => {
    event.preventDefault();
    if (choice === 'link' && !accountId) { setError('Choose a Fynvo account.'); return; }
    const payload = choice === 'link' ? { action: 'link', fynvo_account_id: Number(accountId) } : choice === 'create' ? { action: 'create', name: name.trim(), account_type: accountType } : { action: 'ignore' };
    if (await mapping(setup, payload)) closeSetup();
  };
  const configure = async (event) => {
    event.preventDefault();
    if (await execute('configure', () => apiRequest('/bank-connections/redbark/credentials', { method: 'PUT', body: JSON.stringify({ api_key: apiKey }) }), 'Redbark connected. Review the accounts needing setup.')) setApiKey('');
  };
  const sync = (connection) => execute(`sync:${connection.id}`, () => apiRequest(`/bank-connections/${connection.id}/sync`, { method: 'POST' }), 'Bank accounts refreshed.');
  const disconnect = (connection) => {
    if (window.confirm('Disconnect this bank? Existing Fynvo accounts and imported transaction history will be kept.')) execute(`disconnect:${connection.id}`, () => apiRequest(`/bank-connections/${connection.id}/disconnect`, { method: 'POST' }), 'Bank disconnected. Financial history was preserved.');
  };
  const remove = () => {
    if (window.confirm('Remove the Redbark API key? Fynvo accounts and transaction history will be kept.')) execute('remove', () => apiRequest('/bank-connections/redbark/credentials', { method: 'DELETE' }), 'Redbark removed. Financial history was preserved.');
  };

  return <main className="fynvo-bank-settings">
    <header className="fynvo-bank-settings-head"><div><small>Settings</small><h1>Bank connections</h1><p>Choose how each bank account relates to your Fynvo accounts.</p></div><button ref={backButton} type="button" onClick={onClose}>Back to Fynvo</button></header>
    <div className="fynvo-bank-settings-content">
      {error && <div className="fynvo-bank-alert error" role="alert">{error}</div>}
      {message && <div className="fynvo-bank-alert" role="status">{message}</div>}
      {!state ? <section className="fynvo-bank-card" role="status">Loading bank connections…</section> : <>
        <section className="fynvo-bank-card"><div className="fynvo-bank-card-head"><div><h2>Redbark</h2><p>{state.configured ? `${connectedCount} accounts syncing · ${setupCount} need setup${attentionCount ? ` · ${attentionCount} need attention` : ''}` : 'Connect your banking data'}</p><small>{activeConnections.length ? freshness(activeConnections.reduce((latest, connection) => !latest || (connection.last_successful_sync && connection.last_successful_sync > latest) ? connection.last_successful_sync : latest, null)) : providerState === 'Disconnected' ? 'Sync stopped' : 'No bank accounts discovered'}</small></div><span className="fynvo-bank-state">{providerState}</span></div>
          <p className="fynvo-bank-note">Your API key stays on the Fynvo backend. Only linked accounts affect Fynvo balances and Activity.</p>
          <form className="fynvo-bank-credential" onSubmit={configure}><label><span>{state.configured ? 'Replace API key' : 'Redbark API key'}</span><input type="password" autoComplete="off" minLength="8" required value={apiKey} onChange={(event) => setApiKey(event.target.value)} /></label><button className="primary" disabled={!!busy || !apiKey}>{busy === 'configure' ? 'Checking…' : providerState === 'Disconnected' ? 'Reconnect Redbark' : state.configured ? 'Replace key' : 'Connect Redbark'}</button></form>
          {state.configured && <div className="fynvo-bank-actions"><button disabled={!!busy} onClick={() => execute('test', () => apiRequest('/bank-connections/redbark/test', { method: 'POST' }), 'Connection is working.')}>Test connection</button><button disabled={!!busy} onClick={() => execute('discover', () => apiRequest('/bank-connections/redbark/discover', { method: 'POST' }), 'Accounts refreshed.')}>Refresh accounts</button><button className="danger" disabled={!!busy} onClick={remove}>Remove Redbark</button></div>}
          <p className="fynvo-bank-small">Automatic sync runs approximately every {state.automatic_sync_minutes || 30} minutes. Fynvo does not need to remain open. Redbark supplies posted transactions only.</p>
        </section>
        {groups.map(([key, label]) => { const rows = externalRows.filter((item) => item.state === key && item.connection.status !== 'disconnected'); return rows.length ? <section className="fynvo-bank-card" key={key} aria-label={label}><h2>{label}</h2><div className="fynvo-bank-account-list">{rows.map((item) => <article className="fynvo-bank-account" key={item.id}><div className="fynvo-bank-account-main"><strong>{item.fynvo_account_id ? accounts.find((account) => Number(account.id) === Number(item.fynvo_account_id))?.name || item.name : item.name}</strong><span>{[item.name, item.institution_name, item.masked_identifier].filter(Boolean).join(' · ')}</span><small>{money(item.current_balance)} · {freshness(item.last_successful_sync || item.balance_timestamp)}</small>{item.error_state && <small className="error-text">{item.error_state}</small>}</div><div className="fynvo-bank-row-actions">{key === 'unresolved' && <button type="button" disabled={!!busy} onClick={(event) => begin(item, event)}>Set up account</button>}{key === 'ignored' && <button type="button" disabled={!!busy} onClick={() => mapping(item, { action: 'restore' })}>Start using in Fynvo</button>}{key === 'connected' && <button type="button" disabled={!!busy} onClick={() => { if (window.confirm('Unlink this bank account? The Fynvo account and historical transactions will be kept.')) mapping(item, { action: 'unlink' }); }}>Unlink from Fynvo</button>}{key === 'needs_attention' && <button type="button" disabled={!!busy} onClick={() => sync(item.connection)}>Review connection</button>}</div></article>)}</div></section> : null; })}
        {(state.connections || []).filter((connection) => connection.status !== 'disconnected').map((connection) => <section className="fynvo-bank-card" key={connection.id}><div className="fynvo-bank-card-head"><div><h2>{connection.institution_name}</h2><p>{freshness(connection.last_successful_sync)}</p></div><span className="fynvo-bank-state">{connection.status === 'partial' ? 'Partially updated' : connection.status === 'error' ? 'Needs attention' : 'Connected'}</span></div>{connection.error_state && <p role="status">{connection.error_state}</p>}<div className="fynvo-bank-actions"><button disabled={!!busy} onClick={() => sync(connection)}>Sync now</button><button disabled={!!busy} onClick={() => disconnect(connection)}>Disconnect bank</button></div></section>)}
      </>}
    </div>
    {setup && <div className="fynvo-bank-dialog-backdrop"><section ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="bank-setup-title" className="fynvo-bank-dialog" onKeyDown={(event) => { if (event.key === 'Escape') closeSetup(); if (event.key === 'Tab') { const focusable = [...dialog.current.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled])')]; const first = focusable[0]; const last = focusable.at(-1); if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); } } }}><h2 id="bank-setup-title">Set up {setup.name}</h2><p>{setup.institution_name} · {setup.masked_identifier} · {money(setup.current_balance)}</p><form onSubmit={confirm}><fieldset><legend>How would you like to use this bank account?</legend><label><input type="radio" name="choice" checked={choice === 'link'} onChange={() => setChoice('link')} /> Link to existing Fynvo account</label><label><input type="radio" name="choice" checked={choice === 'create'} onChange={() => setChoice('create')} /> Create new Fynvo account</label><label><input type="radio" name="choice" checked={choice === 'ignore'} onChange={() => setChoice('ignore')} /> Ignore this bank account</label></fieldset>{choice === 'link' && <label>Fynvo account<select required value={accountId} onChange={(event) => setAccountId(event.target.value)}><option value="">Choose an account</option>{sortedCandidates.map((account) => <option key={account.id} value={account.id}>{suggested(setup, account) ? 'Suggested match: ' : ''}{account.name} · {account.institution || 'Manual'} · {money(account.current_balance)}</option>)}</select><small>Suggestions use matching name, institution and type, but are never linked automatically. Review the bank balance against the current Fynvo balance before confirming.</small></label>}{choice === 'create' && <><label>Account name<input required maxLength="120" value={name} onChange={(event) => setName(event.target.value)} /></label><label>Account type<select value={accountType} onChange={(event) => setAccountType(event.target.value)}>{['transaction', 'savings', 'offset', 'credit_card', 'mortgage', 'personal_loan', 'car_loan', 'line_of_credit'].map((type) => <option key={type} value={type}>{type.replaceAll('_', ' ')}</option>)}</select></label><p>The current bank balance will become the opening Fynvo balance.</p></>}{choice === 'ignore' && <p>This account will not affect balances, Activity or your plan. You can restore it later.</p>}{error && <p role="alert">{error}</p>}<div className="fynvo-bank-actions"><button type="button" onClick={closeSetup}>Cancel</button><button className="primary" type="submit" disabled={!!busy}>{busy ? 'Saving…' : choice === 'ignore' ? 'Ignore account' : choice === 'create' ? 'Create and link account' : 'Confirm link'}</button></div></form></section></div>}
  </main>;
}
