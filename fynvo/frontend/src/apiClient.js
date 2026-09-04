export class ApiError extends Error {
  constructor(message, { status = 0, payload = null, path = '' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
    this.path = path;
  }
}

export function apiUrl(path) {
  const clean = String(path || '').replace(/^\/+/, '');
  return `api/${clean}`;
}

const inFlightGets = new Map();
const shortCache = new Map();
const commandCentreByRange = new Map();
const SHORT_CACHE_MS = 10000;

function methodFor(options = {}) {
  return String(options.method || 'GET').toUpperCase();
}

function rangeFromCommandPath(path) {
  const match = String(path || '').match(/dashboard\/command-centre\?[^#]*range_days=(\d+)/);
  return match ? Number(match[1]) : null;
}

function rangeFromForecastPath(path) {
  const match = String(path || '').match(/forecast\?[^#]*mode=expected[^#]*horizon=(\d+)d/);
  return match ? Number(match[1]) : null;
}

function rangeFromHealthPath(path) {
  const match = String(path || '').match(/insights\/financial-health\?[^#]*horizon_days=(\d+)/);
  return match ? Number(match[1]) : null;
}

function freshCached(path) {
  const cached = shortCache.get(path);
  if (!cached || cached.expiresAt <= Date.now()) {
    if (cached) shortCache.delete(path);
    return undefined;
  }
  return cached.payload;
}

function remember(path, payload) {
  shortCache.set(path, { payload, expiresAt: Date.now() + SHORT_CACHE_MS });
  return payload;
}

function clearReadCaches() {
  shortCache.clear();
  commandCentreByRange.clear();
}

async function parseResponse(response, path) {
  const contentType = response.headers.get('content-type') || '';
  let payload = null;
  if (response.status !== 204) {
    try {
      payload = contentType.includes('application/json') ? await response.json() : await response.text();
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const detail = typeof payload === 'object' ? payload?.detail : null;
    const message = typeof detail === 'string' ? detail : `Request failed (${response.status}).`;
    throw new ApiError(message, { status: response.status, payload, path });
  }

  return payload;
}

async function networkRequest(path, options = {}) {
  const started = typeof performance !== 'undefined' ? performance.now() : Date.now();
  const headers = { ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) };
  let response;
  try {
    response = await fetch(apiUrl(path), { credentials: 'same-origin', ...options, headers });
  } catch (error) {
    throw new ApiError('Network request failed. Check the Fynvo connection and try again.', { path, payload: error?.message || null });
  }

  const payload = await parseResponse(response, path);

  if (import.meta.env?.DEV) {
    const ended = typeof performance !== 'undefined' ? performance.now() : Date.now();
    const duration = Math.round(ended - started);
    if (duration >= 750) console.info(`[fynvo] slow request ${response.status} ${path} ${duration}ms`);
  }

  return payload;
}

function commandDerivedRequest(path) {
  const forecastRange = rangeFromForecastPath(path);
  if (forecastRange !== null) {
    const commandPromise = commandCentreByRange.get(forecastRange);
    if (commandPromise) return commandPromise.then((command) => command?.forecast?.expected ?? null);
  }

  const healthRange = rangeFromHealthPath(path);
  if (healthRange !== null) {
    const commandPromise = commandCentreByRange.get(healthRange);
    if (commandPromise) return commandPromise.then((command) => command?.financial_health ?? null);
  }

  return null;
}

export async function apiRequest(path, options = {}) {
  const method = methodFor(options);
  if (method !== 'GET') {
    clearReadCaches();
    return networkRequest(path, options);
  }

  const cached = freshCached(path);
  if (cached !== undefined) return cached;

  const derived = commandDerivedRequest(path);
  if (derived) {
    const promise = derived.then((payload) => remember(path, payload));
    inFlightGets.set(path, promise);
    try {
      return await promise;
    } finally {
      if (inFlightGets.get(path) === promise) inFlightGets.delete(path);
    }
  }

  const existing = inFlightGets.get(path);
  if (existing) return existing;

  const commandRange = rangeFromCommandPath(path);
  const promise = networkRequest(path, options).then((payload) => remember(path, payload));
  inFlightGets.set(path, promise);
  if (commandRange !== null) commandCentreByRange.set(commandRange, promise);

  try {
    return await promise;
  } finally {
    if (inFlightGets.get(path) === promise) inFlightGets.delete(path);
  }
}

export async function apiResult(path, options = {}) {
  try {
    return { ok: true, data: await apiRequest(path, options), error: null };
  } catch (error) {
    return { ok: false, data: null, error };
  }
}
