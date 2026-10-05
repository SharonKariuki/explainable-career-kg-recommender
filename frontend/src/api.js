// Small client for the Django REST API. The token from login is kept in
// localStorage so a page reload keeps the user signed in.

const TOKEN_KEY = 'ajiraguide.token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage unavailable (private mode): the session lasts until reload.
  }
}

export class ApiError extends Error {
  constructor(status, data) {
    super(firstMessage(data) || `Request failed (${status})`)
    this.status = status
    this.data = data
  }
}

// DRF errors look like {"detail": "..."} or {"field": ["..."]}.
function firstMessage(data) {
  if (!data || typeof data !== 'object') return null
  if (typeof data.detail === 'string') return data.detail
  for (const value of Object.values(data)) {
    if (Array.isArray(value) && value.length) return String(value[0])
    if (typeof value === 'string') return value
  }
  return null
}

async function request(method, path, body) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Token ${token}`

  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if (response.status === 401) setToken(null)
  if (!response.ok) throw new ApiError(response.status, data)
  return data
}

export async function register(username, password, email) {
  const data = await request('POST', '/auth/register/', { username, password, email })
  setToken(data.token)
  return data
}

export async function login(username, password) {
  const data = await request('POST', '/auth/login/', { username, password })
  setToken(data.token)
  return data
}

export async function logout() {
  try {
    await request('POST', '/auth/logout/')
  } finally {
    setToken(null)
  }
}

export const me = () => request('GET', '/auth/me/')
export const getProfile = () => request('GET', '/profile/')
export const saveProfile = (skills) => request('PUT', '/profile/', { skills })
export const getRecommendations = (top = 10) => request('GET', `/recommendations/?top=${top}`)
export const getRecommendation = (code) => request('GET', `/recommendations/${encodeURIComponent(code)}/`)
