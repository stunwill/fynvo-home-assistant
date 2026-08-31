import { useEffect } from 'react';
import BaseApp from './AppCorrectiveV0174.jsx';
import './accounts-cards-v1163.css';

export const APP_VERSION_V1163 = '1.16.3';

export default function AppCorrectiveV1163() {
  useEffect(() => {
    const rewriteLegacyCardsNavigation = () => {
      document.querySelectorAll('.nav-group button').forEach((button) => {
        if (button.textContent?.trim() === 'Cards') button.remove();
      });
      const header = document.querySelector('main.content .header');
      const heading = header?.querySelector('h1');
      if (heading?.textContent?.trim() === 'Cards') {
        heading.textContent = 'Accounts';
        localStorage.setItem('fynvo.accountsView', 'cards');
      }
    };
    const observer = new MutationObserver(rewriteLegacyCardsNavigation);
    observer.observe(document.body, { childList: true, subtree: true });
    rewriteLegacyCardsNavigation();
    return () => observer.disconnect();
  }, []);

  return <BaseApp/>;
}
