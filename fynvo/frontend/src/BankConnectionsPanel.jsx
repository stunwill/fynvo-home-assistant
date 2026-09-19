import { useEffect, useMemo, useState } from 'react';
import { apiRequest } from './apiClient.js';
import './bank-connections-v126.css';

const friendlyError = (error) => error?.message || 'Bank connection could not be updated.';

const freshness = (value) => {
  if (!value) return 'Never synced';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'Last sync time unavailable';
  const minutes = Math.max(0, Math.round((Date.now() - parsed.getTime()) / 60000));
  if (minutes < 2) return 'Updated just now';
  if (minutes < 60) return `Updated ${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `Updated ${hours} hr${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  return `Updated ${days} day${days === 1 ? '' : 's'} ago`;
};

export default function BankConnectionsPanel({ onClose }) {
  const [state, setState] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [apiKey, setApiKey] = useState('');
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    setError('');
    try {
      const [banking, fynvoAccounts] = await Promise.all([
        apiRequest('/bank-connections/redbark/status'),
        apiRequest('/accounts'),
      ]);
      setState(banking);
      setAccounts(fynvoAccounts || []);
    } catch (requestError) {
      setError(friendlyError(requestError));
    }
  };
  useEffect(() => { load(); }, []);

  const mappedCount = useMemo(() => (state?.connections || []).flatMap((item) => item.accounts || []).filter((item) => item.fynvo_account_id).length, [state]);

  const configure = async (event) => {
    event.preventDefault();
    setBusy('configure'); setError(''); setMessage('');
    try {
      await apiRequest('/bank-connections/redbark/credentials', { method: 'PUT', body: JSON.stringify({ api_key: apiKey }) });
      setApiKey('');
      setMessage('Redbark connected. Review the discovered bank accounts below.');
      await load();
    } catch (requestError) { setError(friendlyError(requestError)); }
    finally { setBusy(''); }
  };

  const test = async () => {
    setBusy('test'); setError(''); setMessage('');
    try {
      await apiRequest('/bank-connections/redbark/test', { method: 'POST' });
      setMessage('Redbark connection is working.');
    } catch (requestError) { setError(friendlyError(requestError)); }
    finally { setBusy(''); }
  };

  const discover = async () => {
    setBusy('discover'); setError(''); setMessage('');
    try {
      await apiRequest('/bank-connections/redbark/discover', { method: 'POST' });
      setMessage('Bank accounts refreshed.');
      await load();
    } catch (requestError) { setError(friendlyError(requestError)); }
    finally { setBusy(''); }
  };

  const sync = async (connectionId) => {
    setBusy(`sync:${connectionId}`); setError(''); setMessage('');
    try {
      const result = await apiRequest(`/bank-connections/${connectionId}/sync`, { method: 'POST' });
      setMessage(result.accounts_failed ? `${result.accounts_synced} account(s) updated; ${result.accounts_failed} need attention.` : 'Bank data is up to date.');
      await load();
      window.dispatchEvent(new CustomEvent('fynvo:balances-updated'));
    } catch (requestError) { setError(friendlyError(requestError)); }
    finally { setBusy(''); }
  };

  const mapAccount = async (connectionId, externalId, value) => {
    setBusy(`map:${externalId}`); setError('');
    try {
      const payload = value === 'create' ? { action: 'create' } : value === 'ignore' ? { action: 'ignore' } : value === 'unlink' ? { action: 'unlink' } : { action: 'link', fynvo_account_id: Number(value) };
      await apiRequest(`/bank-connections/${connectionId}/accounts/${externalId}/mapping`, { method: 'POST', body: JSON.stringify(payload) });
      await load();
      window.dispatchEvent(new CustomEvent('fynvo:balances-updated'));
    } catch (requestError) { setError(friendlyError(requestError)); }
    finally { setBusy(''); }
  };

  const disconnect = async (connectionId) => {
    if (!window.confirm('Disconnect this bank? Existing Fynvo accounts and imported transaction history will be kept.')) return;
    setBusy(`disconnect:${connectionId}`); setError('');
    try {
      await apiRequest(`/bank-connections/${connectionId}/disconnect`, { method: 'POST' });
      setMessage('Bank disconnected. Existing financial history was preserved.');
      await load();
    } catch (requestError) { setError(friendlyError(requestError)); }
    finally { setBusy(''); }
  };

  const removeCredentials = async () => {
    if (!window.confirm('Remove the Redbark API key and stop future bank synchronisation? Existing accounts and transactions will be kept.')) return;
    setBusy('remove'); setError('');
    try {
      await apiRequest('/bank-connections/redbark/credentials', { method: 'DELETE' });
      setMessage('Redbark credentials removed. Financial history was preserved.');
      await load();
    } catch (requestError) { setError(friendlyError(requestError)); }
    finally { setBusy(''); }
  };

  return <main className="fynvo-bank-settings">
    <header className="fynvo-bank-settings-head">
      <div><small>Settings</small><h1>Bank connections</h1><p>Connect live bank balances and posted transactions to Fynvo through Redbark Open Banking.</p></div>
      <button type="button" onClick={onClose}>Back to Fynvo</button>
    </header>
    <div className="fynvo-bank-settings-content">
      {error && <div className="fynvo-bank-alert error" role="alert"><strong>Bank connection needs attention</strong><span>{error}</span></div>}
      {message && <div className="fynvo-bank-alert" role="status">{message}</div>}
      {!state ? <section className="fynvo-bank-card" role="status">Loading bank connections…</section> : <>
        <section className="fynvo-bank-card">
          <div className="fynvo-bank-card-head"><div><h2>Redbark Open Banking</h2><p>{state.configured ? `Connected · ${mappedCount} mapped account${mappedCount === 1 ? '' : 's'}` : 'Not configured'}</p></div><span className={`fynvo-bank-state ${state.configured ? 'ok' : ''}`}>{state.configured ? 'Configured' : 'Setup required'}</span></div>
          <p className="fynvo-bank-note">Your API key stays in Fynvo's backend data directory and is never returned to this page. Redbark currently supplies posted transactions only.</p>
          <form className="fynvo-bank-credential" onSubmit={configure}>
            <label><span>{state.configured ? 'Replace API key' : 'Redbark API key'}</span><input type="password" autoComplete="off" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={state.configured ? 'Enter a new key to replace the saved key' : 'Paste your Redbark API key'} required minLength="8" /></label>
            <button className="primary" type="submit" disabled={busy || !apiKey}>{busy === 'configure' ? 'Checking…' : state.configured ? 'Replace key' : 'Connect Redbark'}</button>
          </form>
          {state.configured && <div className="fynvo-bank-actions"><button type="button" onClick={test} disabled={busy}>{busy === 'test' ? 'Testing…' : 'Test connection'}</button><button type="button" onClick={discover} disabled={busy}>{busy === 'discover' ? 'Refreshing…' : 'Refresh accounts'}</button><button type="button" className="danger" onClick={removeCredentials} disabled={busy}>Remove Redbark</button></div>}
          <p className="fynvo-bank-small">Automatic sync runs approximately every {state.automatic_sync_minutes || 30} minutes from the Fynvo backend. Fynvo does not need to remain open.</p>
        </section>
        {(state.connections || []).map((connection) => <section className="fynvo-bank-card" key={connection.id}>
          <div className="fynvo-bank-card-head"><div><h2>{connection.institution_name}</h2><p>{freshness(connection.last_successful_sync)}</p></div><span className={`fynvo-bank-state ${connection.status === 'connected' ? 'ok' : connection.status === 'partial' ? 'warn' : ''}`}>{connection.status === 'connected' ? 'Connected' : connection.status === 'partial' ? 'Partially updated' : connection.status}</span></div>
          {connection.error_state && <div className="fynvo-bank-inline-warning" role="status">{connection.error_state}</div>}
          <div className="fynvo-bank-account-list">{(connection.accounts || []).map((external) => <article className="fynvo-bank-account" key={external.id}>
            <div className="fynvo-bank-account-main"><strong>{external.name}</strong><span>{[external.institution_name, external.masked_identifier].filter(Boolean).join(' · ')}</span><small>{external.current_balance == null ? 'Balance unavailable' : `Bank balance $${external.current_balance}`} · {freshness(external.last_successful_sync || external.balance_timestamp)}</small>{external.error_state && <small className="error-text">{external.error_state}</small>}</div>
            <label><span>Fynvo account</span><select value={external.ignored ? 'ignore' : external.fynvo_account_id || ''} disabled={busy === `map:${external.id}`} onChange={(event) => mapAccount(connection.id, external.id, event.target.value)}><option value="">Choose mapping</option><option value="create">Create new Fynvo account</option>{accounts.filter((account) => account.is_active !== false).map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}<option value="ignore">Ignore this bank account</option>{external.fynvo_account_id && <option value="unlink">Unlink from Fynvo</option>}</select></label>
          </article>)}</div>
          <div className="fynvo-bank-actions"><button className="primary" type="button" disabled={busy || connection.status === 'disconnected'} onClick={() => sync(connection.id)}>{busy === `sync:${connection.id}` ? 'Syncing…' : 'Sync now'}</button><button type="button" className="danger" disabled={busy || connection.status === 'disconnected'} onClick={() => disconnect(connection.id)}>Disconnect bank</button></div>
        </section>)}
      </>}
    </div>
  </main>;
}
