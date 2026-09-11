import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import BaseApp from './AppCorrectiveV0174.jsx';
import AccountsCardsWorkspaceV1163 from './AccountsCardsWorkspaceV1163.jsx';
import PaymentCentreMobileV1183 from './PaymentCentreMobileV1183.jsx';
import PaymentWorkspaceV1240 from './PaymentWorkspaceV1240.jsx';
import PlanWorkspaceV1240 from './PlanWorkspaceV1240.jsx';
import { apiRequest } from './apiClient.js';
import './accounts-cards-v1163.css';

export const APP_VERSION_V1163 = '1.16.3';

export default function AppCorrectiveV1163({ authState = null }) {
  const [legacyView, setLegacyView] = useState(() => localStorage.getItem('fynvo.view'));
  const [subview, setSubview] = useState(() => legacyView === 'Cards' ? 'cards' : localStorage.getItem('fynvo.accountsView') || 'accounts');
  const [accounts, setAccounts] = useState([]);
  const [cards, setCards] = useState([]);
  const [mount, setMount] = useState(null);
  const [paymentMount, setPaymentMount] = useState(null);
  const [planMount, setPlanMount] = useState(null);
  const [paymentSupporting, setPaymentSupporting] = useState({ accounts: [], cards: [], categories: [], recurring: [] });

  async function refreshAccountsCards() {
    if (!authState?.authenticated) return;
    try {
      const [accountRows, cardRows] = await Promise.all([apiRequest('/accounts'), apiRequest('/cards?include_inactive=true')]);
      setAccounts(accountRows || []);
      setCards(cardRows || []);
    } catch {
      // The base workspace keeps its own non-blocking error handling. Do not block rendering here.
    }
  }

  async function refreshPaymentSupporting() {
    if (!authState?.authenticated) return;
    try {
      const [accountRows, cardRows, categoryRows, recurringRows] = await Promise.all([
        apiRequest('/accounts'),
        apiRequest('/cards?include_inactive=true'),
        apiRequest('/categories'),
        apiRequest('/recurring-expenses'),
      ]);
      setPaymentSupporting({ accounts: accountRows || [], cards: cardRows || [], categories: categoryRows || [], recurring: recurringRows || [] });
    } catch {
      // Payment Centre loads its operational data independently and remains usable if supporting selectors fail.
    }
  }

  useEffect(() => { refreshAccountsCards(); }, [authState?.authenticated]);
  useEffect(() => { localStorage.setItem('fynvo.accountsView', subview); }, [subview]);
  useEffect(() => { if (paymentMount) refreshPaymentSupporting(); }, [paymentMount, authState?.authenticated]);

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
      const content = document.querySelector('main.content');
      const accountsActive = current === 'Accounts' || current === 'Cards' || current === 'Accounts & Cards';
      const paymentActive = current === 'Payment Centre' && window.matchMedia('(max-width: 980px)').matches;
      const planActive = current === 'Cash Plan' && window.matchMedia('(max-width: 980px)').matches;
      document.body.classList.toggle('fynvo-accounts-cards-v1163-active', accountsActive);
      document.body.classList.toggle('fynvo-plan-v1240-active', planActive);
      if (accountsActive) {
        setLegacyView(current === 'Cards' ? 'Cards' : 'Accounts');
        if (current === 'Cards') {
          setSubview('cards');
          localStorage.setItem('fynvo.accountsView', 'cards');
          localStorage.setItem('fynvo.view', 'Accounts');
        }
        if (heading && current !== 'Accounts & Cards') heading.textContent = 'Accounts & Cards';
        const description = heading?.closest('.header')?.querySelector('p');
        const expectedDescription = 'Manage your accounts and cards in one place.';
        if (description && description.textContent !== expectedDescription) description.textContent = expectedDescription;
        if (content) setMount((currentMount) => currentMount === content ? currentMount : content);
      } else if (current) {
        setLegacyView(current);
        setMount(null);
      }
      setPaymentMount((currentMount) => {
        const nextMount = paymentActive ? content : null;
        return currentMount === nextMount ? currentMount : nextMount;
      });
      setPlanMount((currentMount) => {
        const nextMount = planActive ? content : null;
        return currentMount === nextMount ? currentMount : nextMount;
      });
    };
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    window.addEventListener('resize', sync);
    sync();
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', sync);
      document.body.classList.remove('fynvo-accounts-cards-v1163-active');
      document.body.classList.remove('fynvo-plan-v1240-active');
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

  const openQuickAdd = () => {
    const quick = [...document.querySelectorAll('button')].find((button) => button.textContent?.includes('+ Quick Add') && !button.closest('.payment-v1183-overlay'));
    quick?.click();
  };

  const addBill = () => {
    openQuickAdd();
    window.setTimeout(() => {
      const choice = [...document.querySelectorAll('button')].find((button) => button.textContent?.trim().startsWith('Bill'));
      choice?.click();
    }, 30);
  };

  const navigate = (label) => {
    const button = [...document.querySelectorAll('.nav-group button')].find((item) => item.textContent?.trim() === label);
    button?.click();
  };

  const workspace = mount && (legacyView === 'Accounts' || legacyView === 'Cards')
    ? createPortal(<div className="accounts-cards-v1163-overlay"><AccountsCardsWorkspaceV1163 activeAccounts={accounts} cards={cards} initialView={subview} onViewChange={setSubview} onEditAccount={openAccountEdit} onAddAccount={addAccount} onRefresh={refreshAccountsCards}/></div>, mount)
    : null;

  const paymentWorkspace = paymentMount
    ? createPortal(<div className="payment-v1183-overlay"><PaymentWorkspaceV1240 onNavigate={navigate} onQuickAdd={openQuickAdd} onAddBill={addBill} onRefreshSupporting={refreshPaymentSupporting}/></div>, paymentMount)
    : null;

  const planWorkspace = planMount
    ? createPortal(<div className="plan-v1240-overlay"><PlanWorkspaceV1240 onNavigate={navigate}/></div>, planMount)
    : null;

  return <><BaseApp authState={authState}/>{workspace}{paymentWorkspace}{planWorkspace}</>;
}
