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

export async function apiRequest(path, options = {}) {
  const started = typeof performance !== 'undefined' ? performance.now() : Date.now();
  const headers = { ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) };
  let response;
  try {
    response = await fetch(apiUrl(path), { credentials: 'same-origin', ...options, headers });
  } catch (error) {
    throw new ApiError('Network request failed. Check the Fynvo connection and try again.', { path, payload: error?.message || null });
  }

  const contentType = response.headers.get('content-type') || '';
  let payload = null;
  if (response.status !== 204) {
    try {
      payload = contentType.includes('application/json') ? await response.json() : await response.text();
    } catch {
      payload = null;
    }
  }

  if (import.meta.env?.DEV) {
    const ended = typeof performance !== 'undefined' ? performance.now() : Date.now();
    const duration = Math.round(ended - started);
    if (duration >= 750) console.info(`[fynvo] slow request ${response.status} ${path} ${duration}ms`);
  }

  if (!response.ok) {
    const detail = typeof payload === 'object' ? payload?.detail : null;
    const message = typeof detail === 'string' ? detail : `Request failed (${response.status}).`;
    throw new ApiError(message, { status: response.status, payload, path });
  }

  return payload;
}

export async function apiResult(path, options = {}) {
  try {
    return { ok: true, data: await apiRequest(path, options), error: null };
  } catch (error) {
    return { ok: false, data: null, error };
  }
}
