import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import BaseApp from './AppCorrectiveV0174.jsx';
import AccountsCardsWorkspaceV1163 from './AccountsCardsWorkspaceV1163.jsx';
import './accounts-cards-v1163.css';

export const APP_VERSION_V1163 = '1.16.3';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

export default function AppCorrectiveV1163({ authState = null }) {
  if (authState) globalThis.__fynvoSharedAuthState = authState;
  const [legacyView, setLegacyView] = useState(() => localStorage.getItem('fynvo.view'));
  const [subview, setSubview] = useState(() => legacyView === 'Cards' ? 'cards' : localStorage.getItem('fynvo.accountsView') || 'accounts');
  const [accounts, setAccounts] = useState([]);
  const [cards, setCards] = useState([]);
  const [mount, setMount] = useState(null);

  async function refreshAccountsCards() {
    const [accountResponse, cardResponse] = await Promise.all([api('/accounts'), api('/cards?include_inactive=true')]);
    if (accountResponse.ok) setAccounts(await accountResponse.json());
    if (cardResponse.ok) setCards(await cardResponse.json());
  }

  useEffect(() => { refreshAccountsCards(); }, []);
  useEffect(() => { localStorage.setItem('fynvo.accountsView', subview); }, [subview]);

  useEffect(() => {
    const sync = () => {
      const navButtons = [...document.querySelectorAll('.nav-group button')];
      navButtons.forEach((button) => {
        if (button.textContent?.trim() === 'Cards') button.remove();
      });
      const accountButton = navButtons.find((button) => button.textContent?.trim() === 'Accounts');
      if (accountButton && !accountButton.dataset.v1163Bound) {
        accountButton.dataset.v1163Bound = 'true';
        accountButton.addEventListener('click', () => {
          setLegacyView('Accounts');
          setSubview('accounts');
          localStorage.setItem('fynvo.view', 'Accounts');
          refreshAccountsCards();
        }, true);
      }
      const heading = document.querySelector('main.content .header h1');
      const current = heading?.textContent?.trim();
      const accountsActive = current === 'Accounts' || current === 'Cards' || current === 'Accounts & Cards';
      document.body.classList.toggle('fynvo-accounts-cards-v1163-active', accountsActive);
      if (accountsActive) {
        setLegacyView(current === 'Cards' ? 'Cards' : 'Accounts');
        if (current === 'Cards') {
          setSubview('cards');
          localStorage.setItem('fynvo.accountsView', 'cards');
          localStorage.setItem('fynvo.view', 'Accounts');
        }
        if (heading && current !== 'Accounts & Cards') heading.textContent = 'Accounts & Cards';
        const description = heading?.closest('.header')?.querySelector('p');
        if (description) description.textContent = 'Manage your accounts and cards in one place.';
        const content = document.querySelector('main.content');
        if (content) setMount(content);
      } else if (current) {
        setLegacyView(current);
        setMount(null);
      }
    };
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    sync();
    return () => {
      observer.disconnect();
      document.body.classList.remove('fynvo-accounts-cards-v1163-active');
    };
  }, []);

  const openAccountEdit = (account) => {
    const accountButton = [...document.querySelectorAll('.nav-group button')].find((button) => button.textContent?.trim() === 'Accounts');
    accountButton?.click();
    window.setTimeout(() => {
      const row = [...document.querySelectorAll('main.content button')].find((button) => button.textContent?.includes(account.name) && !button.closest('.accounts-cards-v1163-overlay'));
      row?.click();
    }, 60);
  };

  const addAccount = () => {
    const quick = [...document.querySelectorAll('button')].find((button) => button.textContent?.includes('+ Quick Add'));
    quick?.click();
    window.setTimeout(() => {
      const choice = [...document.querySelectorAll('button')].find((button) => button.textContent?.trim().startsWith('Account'));
      choice?.click();
    }, 30);
  };

  const workspace = mount && (legacyView === 'Accounts' || legacyView === 'Cards')
    ? createPortal(<div className="accounts-cards-v1163-overlay"><AccountsCardsWorkspaceV1163 activeAccounts={accounts} cards={cards} initialView={subview} onViewChange={setSubview} onEditAccount={openAccountEdit} onAddAccount={addAccount} onRefresh={refreshAccountsCards}/></div>, mount)
    : null;

  return <><BaseApp authState={authState}/>{workspace}</>;
}
