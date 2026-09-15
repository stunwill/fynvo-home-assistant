import { useEffect, useState } from 'react';
import App from './AppCorrectiveV1163.jsx';
import HouseholdControlCenter from './HouseholdControlCenter.jsx';
import LoginPage from './LoginPage.jsx';
// Keep the historical integration name stable while the v1.24 redesign replaces its implementation.
import MobileOverviewV1190 from './MobileOverviewV1240.jsx';
import V11ControlCenter from './V11ControlCenter.jsx';
import V13CashFlowPage from './V13CashFlowPage.jsx';

const nativeFetch = window.fetch.bind(window);
const api = (path, options = {}) => nativeFetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});
const PRODUCTION_VERSION = '1.24.2';
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
  const [session, setSession] = useState({ loading: true, authenticated: false, user: null });
  const [activePage, setActivePage] = useState('overview');
  const [security, setSecurity] = useState({ loading: true, available: false, data: null });

  const loadSession = async () => {
    publishStartup('session-check');
    try {
      const response = await api('/auth/session');
      if (!response.ok) throw new Error(`Session check failed (${response.status})`);
      const data = await response.json();
      setSession({ loading: false, authenticated: Boolean(data.authenticated), user: data.user || null });
      publishStartup(data.authenticated ? 'authenticated' : 'login-required');
    } catch (error) {
      console.error('Session bootstrap failed', error);
      setSession({ loading: false, authenticated: false, user: null });
      publishStartup('session-error', error.message);
    }
  };

  useEffect(() => {
    loadSession();
  }, []);

  useEffect(() => {
    if (!session.authenticated) {
      setSecurity({ loading: false, available: false, data: null });
      return undefined;
    }

    let cancelled = false;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), HOUSEHOLD_SECURITY_TIMEOUT_MS);
    setSecurity((current) => ({ ...current, loading: true }));
    api('/household/security', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Household security failed (${response.status})`);
        const data = await response.json();
        if (!cancelled) setSecurity({ loading: false, available: true, data });
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn('Household security unavailable', error);
          setSecurity({ loading: false, available: false, data: null });
        }
      })
      .finally(() => window.clearTimeout(timeout));

    return () => {
      cancelled = true;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [session.authenticated]);

  if (session.loading) {
    return <div className="app-loading">Loading Fynvo…</div>;
  }

  if (!session.authenticated) {
    return <LoginPage onAuthenticated={loadSession} />;
  }

  const sharedProps = {
    activePage,
    setActivePage,
    user: session.user,
    security: security.data,
    securityAvailable: security.available,
  };

  if (activePage === 'overview') {
    return <MobileOverviewV1190 {...sharedProps} />;
  }
  if (activePage === 'household') {
    return <HouseholdControlCenter {...sharedProps} />;
  }
  if (activePage === 'cash-flow') {
    return <V13CashFlowPage {...sharedProps} />;
  }
  if (activePage === 'control-center') {
    return <V11ControlCenter {...sharedProps} />;
  }

  return <App {...sharedProps} initialPage={activePage} />;
}
