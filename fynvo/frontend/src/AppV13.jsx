import { useEffect, useState } from 'react';
import App from './AppCorrectiveV1163.jsx';
import HouseholdControlCenter from './HouseholdControlCenter.jsx';
import LoginPage from './LoginPage.jsx';
import V11ControlCenter from './V11ControlCenter.jsx';
import V13CashFlowPage from './V13CashFlowPage.jsx';

const nativeFetch = window.fetch.bind(window);
const api = (path, options = {}) => nativeFetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});
const PRODUCTION_VERSION = '1.17.7';
const HOUSEHOLD_SECURITY_TIMEOUT_MS = 3500;

function publishStartup(stage, detail = '') {
  globalThis.__fynvoStartupStage = stage;
  console.info(`[Fynvo startup] ${stage}${detail ? `: ${detail}` : ''}`);
  if (['authenticated', 'workspace-mounted', 'workspace-rendered'].includes(stage)) {
    nativeFetch('api/household/client-diagnostics', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stage, detail, version: PRODUCTION_VERSION }),
    }).catch(() => {});
  }
}

export default function AppV13() {
  const [auth, setAuth] = useState(null);
  const [recoveryWarningDismissed, setRecoveryWarningDismissed] = useState(false);
  const [v11Mode, setV11Mode] = useState(null);
  const [v13CashFlowOpen, setV13CashFlowOpen] = useState(false);
  const [householdOpen, setHouseholdOpen] = useState(false);
  const [householdSecurity, setHouseholdSecurity] = useState(null);
  const [householdSecurityError, setHouseholdSecurityError] = useState('');
  const [toolsOpen, setToolsOpen] = useState(false);

  async function refreshAuth() {
    publishStartup('auth-request');
    try {
      const response = await api('/auth/state');
      if (!response.ok) throw new Error('auth-state');
      const state = await response.json();
      setAuth(state);
      publishStartup(state.authenticated ? 'authenticated' : 'anonymous');
      return state;
    } catch {
      const unavailable = { authenticated: false, setup_required: false, user: null, message: 'Authentication service unavailable.' };
      setAuth(unavailable);
      publishStartup('auth-error');
      return null;
    }
  }

  async function refreshHouseholdSecurity() {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), HOUSEHOLD_SECURITY_TIMEOUT_MS);
    setHouseholdSecurityError('');
    try {
      const response = await api('/household/me/security', { signal: controller.signal });
      if (!response.ok) throw new Error('household-security');
      const state = await response.json();
      setHouseholdSecurity(state);
      return state;
    } catch {
      setHouseholdSecurityError('Household security status could not be refreshed.');
      return null;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  useEffect(() => { refreshAuth(); }, []);
  useEffect(() => {
    if (auth?.authenticated) refreshHouseholdSecurity();
    else {
      setHouseholdSecurity(null);
      setHouseholdSecurityError('');
    }
  }, [auth?.authenticated, auth?.user?.id]);
  useEffect(() => {
    if (!auth?.authenticated) return undefined;
    publishStartup('workspace-mounted');
    let renderedReported = false;
    const syncProductionShell = () => {
      const heading = document.querySelector('main.content .header h1')?.textContent?.trim();
      if (heading && !renderedReported) {
        renderedReported = true;
        publishStartup('workspace-rendered', heading);
      }
      document.body.classList.toggle('fynvo-income-page', heading === 'Income');
      const footer = document.querySelector('.app-footer');
      const expectedVersion = `Fynvo v${PRODUCTION_VERSION}`;
      if (footer && footer.textContent !== expectedVersion) footer.textContent = expectedVersion;
    };
    const observer = new MutationObserver(syncProductionShell);
    observer.observe(document.body, { childList: true, subtree: true });
    syncProductionShell();
    return () => { observer.disconnect(); document.body.classList.remove('fynvo-income-page'); };
  }, [auth?.authenticated]);

  const openTool = (mode) => { setToolsOpen(false); if (mode === 'cash-flow') setV13CashFlowOpen(true); else if (mode === 'household') setHouseholdOpen(true); else setV11Mode(mode); };
  if (!auth) return <main className="fynvo-auth-page"><section className="fynvo-auth-form-panel"><div className="fynvo-auth-card" role="status">Loading Fynvo…</div></section></main>;
  if (!auth.authenticated) return <LoginPage authState={auth} onStateRefresh={refreshAuth} onAuthenticated={async () => { await refreshAuth(); }}/>;
  if (householdSecurity?.must_change_password) return <HouseholdControlCenter forcePasswordChange onPasswordChanged={async () => { setHouseholdSecurity(null); await refreshAuth(); refreshHouseholdSecurity(); }}/>;
  if (householdOpen) return <HouseholdControlCenter onClose={() => setHouseholdOpen(false)}/>;
  if (v13CashFlowOpen) return <V13CashFlowPage onClose={() => setV13CashFlowOpen(false)}/>;
  if (v11Mode) return <V11ControlCenter mode={v11Mode} onClose={() => setV11Mode(null)}/>;

  return <>
    {auth.recovery_mode && !recoveryWarningDismissed && <div className="fynvo-recovery-warning" role="status" aria-live="polite"><span><strong>Administrator recovery mode is enabled.</strong> Confirm this login works, then disable <code>admin_recovery_mode</code> in the Home Assistant add-on Configuration page and restart Fynvo.</span><button type="button" onClick={() => setRecoveryWarningDismissed(true)} aria-label="Dismiss administrator recovery warning">Dismiss</button></div>}
    <App authState={auth}/>
    {householdSecurityError && <div className="fynvo-startup-recovery fynvo-household-security-warning" role="status"><strong>Household security status unavailable.</strong><span>Fynvo has continued loading. Retry the household security check when convenient.</span><button type="button" onClick={refreshHouseholdSecurity}>Retry security check</button></div>}
    <div className="fynvo-tools-menu-shell"><button type="button" className="fynvo-tools-menu-trigger" aria-expanded={toolsOpen} aria-controls="fynvo-tools-menu" onClick={() => setToolsOpen((value) => !value)}>Tools</button>{toolsOpen && <nav id="fynvo-tools-menu" className="fynvo-tools-menu" aria-label="Fynvo tools"><button type="button" onClick={() => openTool('cash-flow')}>Cash Flow Intelligence</button><button type="button" onClick={() => openTool('household')}>Household</button><button type="button" onClick={() => openTool('coverage')}>Data Coverage</button><button type="button" onClick={() => openTool('splits')}>Split Transaction</button><button type="button" onClick={() => openTool('security')}>Security & MFA</button><button type="button" onClick={() => openTool('export')}>Data Export</button></nav>}</div>
  </>;
}
