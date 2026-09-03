const BASE = ''

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  let data = null
  try {
    data = await res.json()
  } catch (_) {
    // no JSON body (e.g. 204/empty) — leave data null
  }
  if (!res.ok) {
    const message = (data && data.detail) || res.statusText || 'Request failed'
    const err = new Error(message)
    err.status = res.status
    throw err
  }
  return data
}

export const api = {
  login: (username, password) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  me: () => request('/api/auth/me'),

  listEnvironments: () => request('/api/environments'),
  capacity: () => request('/api/environments/capacity'),
  createEnvironment: (name, server_count) =>
    request('/api/environments', { method: 'POST', body: JSON.stringify({ name, server_count }) }),
  getEnvironment: (uuid) => request(`/api/environments/${uuid}`),
  getEnvironmentEvents: (uuid) => request(`/api/environments/${uuid}/events`),
  deleteEnvironment: (uuid) => request(`/api/environments/${uuid}`, { method: 'DELETE' }),
  retryDelete: (uuid) => request(`/api/environments/${uuid}/retry-delete`, { method: 'POST' }),
  dismissDelete: (uuid) => request(`/api/environments/${uuid}/dismiss-delete`, { method: 'POST' }),
  testConnectivity: (uuid, serverId) =>
    request(`/api/environments/${uuid}/connectivity-test/${serverId}`, { method: 'POST' }),
}
