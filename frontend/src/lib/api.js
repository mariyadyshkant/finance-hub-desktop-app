// La porta del backend è scelta dinamicamente da Electron (vedi
// electron/main.js: findFreePort) — 8000 può essere occupata da altri
// servizi sulla macchina dell'utente, quindi non possiamo assumerla fissa.
// financedAPI è esposta dal preload solo dentro Electron; in fallback
// (es. `vite dev` aperto in un browser normale, fuori da Electron) si
// assume comunque 8000.
let basePromise;

function resolveBackendPort() {
  if (window.financedAPI?.getBackendPort) {
    return window.financedAPI.getBackendPort();
  }
  return Promise.resolve(8000);
}

export function apiBaseUrl() {
  if (!basePromise) {
    basePromise = resolveBackendPort().then((port) => `http://127.0.0.1:${port}`);
  }
  return basePromise;
}

async function request(path, options = {}) {
  const base = await apiBaseUrl();
  const res = await fetch(`${base}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} — ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: "DELETE" }),
};
