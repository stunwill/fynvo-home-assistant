import { useEffect, useRef, useState } from 'react';
import App from './AppCorrectiveV0174.jsx';
import HouseholdControlCenter from './HouseholdControlCenter.jsx';
import LoginPage from './LoginPage.jsx';
import V11ControlCenter from './V11ControlCenter.jsx';
import V13CashFlowPage from './V13CashFlowPage.jsx';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});
const PRODUCTION_VERSION = '1.10.1';

export default function AppV13() {
  const [auth, setAuth] = useState(null);
  const [recoveryWarningDismissed, setRecoveryWarningDismissed] = useState(false);
  const [v11Mode, setV11Mode] = useState(null);
  const [v13CashFlowOpen, setV13CashFlowOpen] = useState(false);
  const [householdOpen, setHouseholdOpen] = useState(false);
  const [householdSecurity, setHouseholdSecurity] = useState(null);
  const [toolsOpen, setToolsOpen] = useState(false);
  const observerRef = useRef(null);

  async function refreshAuth() {
    try {
      const response = await api('/auth/state');
      if (!response.ok) throw new Error('auth-state');
      const state = await response.json();
      setAuth(state);
      return state;
    } catch {
      setAuth({ authenticated: false, setup_required: false, user: null, message: 'Authentication service unavailable.' });
      return null;
    }
  }

  async function refreshHouseholdSecurity() {
    try {
      const response = await api('/household/me/security');
      if (!response.ok) throw new Error('household-security');
      const state = await response.json();
      setHouseholdSecurity(state);
      return state;
    } catch {
      setHouseholdSecurity({ must_change_password: false, mfa_enabled: false, active_session_count: 0 });
      return null;
    }
  }

  useEffect(() => { refreshAuth(); }, []);
  useEffect(() => { if (auth?.authenticated) refreshHouseholdSecurity(); else setHouseholdSecurity(null); }, [auth?.authenticated, auth?.user?.id]);
  useEffect(() => {
    if (!auth?.authenticated) return undefined;
    const syncProductionShell = () => {
      const heading = document.querySelector('main.content .header h1')?.textContent?.trim();
      document.body.classList.toggle('fynvo-income-page', heading === 'Income');
      const footer = document.querySelector('.app-footer');
      const expectedVersion = `Fynvo v${PRODUCTION_VERSION}`;
      if (footer && footer.textContent !== expectedVersion) footer.textContent = expectedVersion;
    };
    const observer = new MutationObserver(() => {
      syncProductionShell();
      if (document.querySelector('main.login')) refreshAuth();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    observerRef.current = observer;
    syncProductionShell();
    return () => { observer.disconnect(); document.body.classList.remove('fynvo-income-page'); };
  }, [auth?.authenticated]);

  const openTool = (mode) => { setToolsOpen(false); if (mode === 'cash-flow') setV13CashFlowOpen(true); else if (mode === 'household') setHouseholdOpen(true); else setV11Mode(mode); };
  if (!auth) return <main className="fynvo-auth-page"><section className="fynvo-auth-form-panel"><div className="fynvo-auth-card" role="status">Loading Fynvo…</div></section></main>;
  if (!auth.authenticated) return <LoginPage authState={auth} onStateRefresh={refreshAuth} onAuthenticated={async () => { await refreshAuth(); }}/>;
  if (!householdSecurity) return <main className="fynvo-auth-page"><section className="fynvo-auth-form-panel"><div className="fynvo-auth-card" role="status">Loading Household identity…</div></section></main>;
  if (householdSecurity.must_change_password) return <HouseholdControlCenter forcePasswordChange onPasswordChanged={async () => { setHouseholdSecurity(null); await refreshAuth(); }}/>;
  if (householdOpen) return <HouseholdControlCenter onClose={() => setHouseholdOpen(false)}/>;
  if (v13CashFlowOpen) return <V13CashFlowPage onClose={() => setV13CashFlowOpen(false)}/>;
  if (v11Mode) return <V11ControlCenter mode={v11Mode} onClose={() => setV11Mode(null)}/>;

  return <>
    {auth.recovery_mode && !recoveryWarningDismissed && <div className="fynvo-recovery-warning" role="status" aria-live="polite"><span><strong>Administrator recovery mode is enabled.</strong> Confirm this login works, then disable <code>admin_recovery_mode</code> in the Home Assistant add-on Configuration page and restart Fynvo.</span><button type="button" onClick={() => setRecoveryWarningDismissed(true)} aria-label="Dismiss administrator recovery warning">Dismiss</button></div>}
    <App />
    <div className="fynvo-tools-menu-shell"><button type="button" className="fynvo-tools-menu-trigger" aria-expanded={toolsOpen} aria-controls="fynvo-tools-menu" onClick={() => setToolsOpen((value) => !value)}>Tools</button>{toolsOpen && <nav id="fynvo-tools-menu" className="fynvo-tools-menu" aria-label="Fynvo tools"><button type="button" onClick={() => openTool('cash-flow')}>Cash Flow Intelligence</button><button type="button" onClick={() => openTool('household')}>Household</button><button type="button" onClick={() => openTool('coverage')}>Data Coverage</button><button type="button" onClick={() => openTool('splits')}>Split Transaction</button><button type="button" onClick={() => openTool('security')}>Security & MFA</button><button type="button" onClick={() => openTool('export')}>Data Export</button></nav>}</div>
  </>;
}
