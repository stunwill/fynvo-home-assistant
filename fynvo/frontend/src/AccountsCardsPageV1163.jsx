import { useMemo, useState } from 'react';

const money = (value) => {
  if (value === null || value === undefined || value === '') return '—';
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' }).format(number);
};

export default function AccountsCardsPageV1163({ accounts, cards, onEditAccount, onAddAccount, onEditCard, onAddCard, initialView = 'accounts' }) {
  const [view, setView] = useState(initialView === 'cards' ? 'cards' : 'accounts');
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('active');

  const visibleAccounts = useMemo(() => accounts.filter((account) => {
    const statusMatch = filter === 'all' || (filter === 'archived' ? Boolean(account.archived_at || account.is_active === false) : !account.archived_at && account.is_active !== false);
    const needle = search.trim().toLowerCase();
    const textMatch = !needle || [account.name, account.institution, account.account_type, account.account_suffix].some((value) => String(value || '').toLowerCase().includes(needle));
    return statusMatch && textMatch;
  }), [accounts, filter, search]);

  const visibleCards = useMemo(() => cards.filter((card) => {
    const statusMatch = filter === 'all' || (filter === 'inactive' ? card.is_active === false : card.is_active !== false);
    const needle = search.trim().toLowerCase();
    const textMatch = !needle || [card.name, card.display_name, card.last_four, card.card_type, card.account_name].some((value) => String(value || '').toLowerCase().includes(needle));
    return statusMatch && textMatch;
  }), [cards, filter, search]);

  const totalBalance = accounts.filter((account) => !account.archived_at && account.is_active !== false).reduce((sum, account) => sum + Number(account.current_balance || 0), 0);
  const activeCards = cards.filter((card) => card.is_active !== false).length;

  const switchView = (next) => {
    setView(next);
    setSearch('');
    setFilter('active');
  };

  return <section className="accounts-cards-v1163">
    <div className="accounts-cards-v1163-head">
      <div><h2>Accounts &amp; Cards</h2><p>Manage your accounts and cards in one place.</p></div>
      <button type="button" className="primary" onClick={view === 'accounts' ? onAddAccount : onAddCard}>+ {view === 'accounts' ? 'Add Account' : 'Add Card'}</button>
    </div>

    <div className="accounts-cards-tabs" role="tablist" aria-label="Accounts and Cards views">
      <button type="button" role="tab" aria-selected={view === 'accounts'} className={view === 'accounts' ? 'active' : ''} onClick={() => switchView('accounts')}>▦ Accounts</button>
      <button type="button" role="tab" aria-selected={view === 'cards'} className={view === 'cards' ? 'active' : ''} onClick={() => switchView('cards')}>▭ Cards</button>
    </div>

    <div className="accounts-cards-summary">
      {view === 'accounts' ? <>
        <article><span>▦</span><small>Total accounts</small><strong>{accounts.length}</strong><em>{accounts.filter((account) => !account.archived_at && account.is_active !== false).length} active</em></article>
        <article><span>▭</span><small>Total cards</small><strong>{cards.length}</strong><em>{activeCards} active</em></article>
        <article><span>＄</span><small>Total balance</small><strong>{money(totalBalance)}</strong><em>Active accounts</em></article>
        <article><span>✓</span><small>Archived</small><strong>{accounts.filter((account) => account.archived_at || account.is_active === false).length}</strong><em>Accounts</em></article>
      </> : <>
        <article><span>▭</span><small>Total cards</small><strong>{cards.length}</strong><em>{activeCards} active</em></article>
        <article><span>✓</span><small>Active cards</small><strong>{activeCards}</strong><em>{cards.length ? `${Math.round((activeCards / cards.length) * 100)}% of total` : 'No cards yet'}</em></article>
        <article><span>▦</span><small>Linked accounts</small><strong>{new Set(cards.map((card) => card.account_id).filter(Boolean)).size}</strong><em>With cards</em></article>
        <article><span>○</span><small>Inactive cards</small><strong>{cards.length - activeCards}</strong><em>Not selectable</em></article>
      </>}
    </div>

    <div className="accounts-cards-toolbar">
      <label><span className="sr-only">Search {view}</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={view === 'accounts' ? 'Search accounts…' : 'Search cards…'}/></label>
      <select aria-label={`Filter ${view}`} value={filter} onChange={(event) => setFilter(event.target.value)}>
        {view === 'accounts' ? <><option value="active">Active</option><option value="archived">Archived</option><option value="all">All</option></> : <><option value="active">Active</option><option value="inactive">Inactive</option><option value="all">All</option></>}
      </select>
    </div>

    {view === 'accounts' ? <div className="accounts-cards-list">
      <div className="accounts-cards-list-title">Accounts ({visibleAccounts.length})</div>
      {visibleAccounts.length ? visibleAccounts.map((account) => {
        const linked = cards.filter((card) => Number(card.account_id) === Number(account.id));
        return <button type="button" className="accounts-cards-account-row" key={account.id} onClick={() => onEditAccount(account)}>
          <span className="accounts-cards-avatar">{String(account.institution || account.name || 'A').slice(0, 3).toUpperCase()}</span>
          <span className="accounts-cards-primary"><strong>{account.name}</strong><small>{account.institution || account.account_type} · {account.account_suffix ? `•••• ${account.account_suffix}` : 'Account'}</small></span>
          <span className={`accounts-cards-status ${account.archived_at || account.is_active === false ? 'archived' : ''}`}>{account.archived_at || account.is_active === false ? 'Archived' : 'Active'}</span>
          <span className="accounts-cards-balance"><strong>{money(account.current_balance ?? account.opening_balance)}</strong><small>Current balance</small></span>
          <span className="accounts-cards-count">▭ {linked.length} card{linked.length === 1 ? '' : 's'}</span>
          <span className="accounts-cards-chevron">›</span>
        </button>;
      }) : <div className="empty"><strong>No accounts found</strong><p>{filter === 'archived' ? 'Archived accounts will appear here.' : 'Add an Account to get started.'}</p></div>}
      <button type="button" className="accounts-cards-bottom-action" onClick={onAddAccount}>+ Add Account</button>
    </div> : <div className="accounts-cards-list">
      <div className="accounts-cards-list-title">Cards ({visibleCards.length})</div>
      {visibleCards.length ? visibleCards.map((card) => <button type="button" className="accounts-cards-card-row" key={card.id} onClick={() => onEditCard(card)}>
        <span className="accounts-cards-card-visual">{card.card_type === 'credit' ? 'CREDIT' : 'CARD'}</span>
        <span className="accounts-cards-primary"><strong>{card.name || card.display_name}</strong><small>•••• {card.last_four} · {String(card.card_type || 'card').replaceAll('_', ' ')}</small><small>Linked account: {card.account_name || 'Unknown account'}</small></span>
        <span className={`accounts-cards-status ${card.is_active === false ? 'archived' : ''}`}>{card.is_active === false ? 'Inactive' : 'Active'}</span>
        <span className="accounts-cards-chevron">›</span>
      </button>) : <div className="empty"><strong>No cards added yet</strong><p>Add your first card to manage and track your household cards.</p><button type="button" className="link-button" onClick={onAddCard}>+ Add Card</button></div>}
      <button type="button" className="accounts-cards-bottom-action" onClick={onAddCard}>+ Add Card</button>
    </div>}
  </section>;
}
