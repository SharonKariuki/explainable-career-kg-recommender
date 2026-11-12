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

export const OFFLINE_MESSAGE = "Can't reach AjiraGuide. Check your internet connection and try again."
export const SIGNED_OUT_EVENT = 'ajiraguide:signed-out'

// The hosted backend sleeps when idle; while it starts, the gateway answers
// 502, 503 or 504. Those requests never reached the app, so they are safe to
// repeat: wait and retry for about a minute before giving up.
const WAKING_STATUSES = new Set([502, 503, 504])
const WAKING_RETRY_MS = [2000, 3000, 5000, 8000, 10000, 12000, 15000]

const wakingListeners = new Set()

// Calls listener(true) while requests wait for the backend to start, then listener(false).
export function onWaking(listener) {
  wakingListeners.add(listener)
  return () => wakingListeners.delete(listener)
}

function setWaking(waking) {
  wakingListeners.forEach((listener) => listener(waking))
}

export class ApiError extends Error {
  constructor(status, data, message) {
    super(message ?? describe(status, data))
    this.status = status
    this.data = data
  }
}

const FIELD_LABELS = {
  username: 'Username',
  password: 'Password',
  email: 'Email',
  current_password: 'Current password',
  new_password: 'New password',
  confirm: 'Confirmation',
  skills: 'Skills',
  education_level: 'Education level',
  field_of_study: 'Field of study',
  interests: 'Career interests',
  experience: 'Experience',
  top: 'Number of results',
}

// DRF errors look like {"detail": "..."}, {"non_field_errors": ["..."]} or
// {"field": ["..."]}; every message is kept, with its field named.
function messagesOf(data, field = null) {
  if (typeof data === 'string') {
    const label = field && field !== 'detail' && field !== 'non_field_errors' ? FIELD_LABELS[field] ?? field : null
    return [label ? `${label}: ${data}` : data]
  }
  if (Array.isArray(data)) return data.flatMap((item) => messagesOf(item, field))
  if (data && typeof data === 'object') {
    return Object.entries(data).flatMap(([key, value]) => messagesOf(value, /^\d+$/.test(key) ? field : key))
  }
  return []
}

function describe(status, data) {
  const detail = messagesOf(data).join(' ')
  if (status === 400) return detail || 'Some details need fixing. Check the form and try again.'
  if (status === 401) return 'Your session has ended. Please sign in again.'
  if (status === 403) return detail || "You don't have permission to do that."
  if (status === 404) return detail || "We couldn't find that. It may have been removed."
  if (status === 429) return 'Too many attempts. Please wait a minute and try again.'
  if (WAKING_STATUSES.has(status)) return 'AjiraGuide is taking longer than usual to start. Please try again in a minute.'
  if (status >= 500) return 'Something went wrong on our side. Please try again, and if it keeps happening, let us know.'
  return detail || `Something went wrong (error ${status}). Please try again.`
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function request(method, path, body) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Token ${token}`

  for (let attempt = 0; ; attempt++) {
    let response
    try {
      response = await fetch(`/api${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      })
    } catch {
      setWaking(false)
      throw new ApiError(0, null, OFFLINE_MESSAGE)
    }
    if (WAKING_STATUSES.has(response.status) && attempt < WAKING_RETRY_MS.length) {
      setWaking(true)
      await wait(WAKING_RETRY_MS[attempt])
      continue
    }
    setWaking(false)

    const data = response.status === 204 ? null : await response.json().catch(() => null)
    if (response.status === 401) {
      setToken(null)
      if (token) window.dispatchEvent(new Event(SIGNED_OUT_EVENT))
    }
    if (!response.ok) throw new ApiError(response.status, data)
    return data
  }
}

export async function register(username, password, email, name = '') {
  const data = await request('POST', '/auth/register/', { username, password, email, name })
  setToken(data.token)
  return data
}

export async function login(username, password) {
  const data = await request('POST', '/auth/login/', { username, password })
  setToken(data.token)
  return data
}

export async function googleLogin(credential) {
  const data = await request('POST', '/auth/google/', { credential })
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
// Sends only what it is given: { skills }, or the background fields as well.
export const saveProfile = (changes) => request('PUT', '/profile/', Array.isArray(changes) ? { skills: changes } : changes)
export const getRecommendations = (top = 10) => request('GET', `/recommendations/?top=${top}`)
export const getRecommendation = (code) => request('GET', `/recommendations/${encodeURIComponent(code)}/`)

export const getCareers = () => request('GET', '/careers/')
export const getCareer = (code) => request('GET', `/careers/${encodeURIComponent(code)}/`)
export const getSaved = () => request('GET', '/saved/')
export const saveCareer = (code) => request('PUT', `/saved/${encodeURIComponent(code)}/`)
export const unsaveCareer = (code) => request('DELETE', `/saved/${encodeURIComponent(code)}/`)
export const searchSkills = (query) => request('GET', `/skills/?q=${encodeURIComponent(query)}`)
export const getProgress = () => request('GET', '/progress/')
export const getHistory = () => request('GET', '/history/')
export const getHistoryRun = (id) => request('GET', `/history/${encodeURIComponent(id)}/`)
export const setProgress = (skillId, status) => request('PUT', '/progress/', { skill_id: skillId, status })
// Sends only the fields given, e.g. { email } or { name, email }.
export const updateAccount = (changes) => request('PATCH', '/auth/me/', changes)

// Changing the password replaces the token, signing out anyone holding the old one.
export async function changePassword(currentPassword, newPassword) {
  const data = await request('POST', '/auth/password/', { current_password: currentPassword, new_password: newPassword })
  setToken(data.token)
  return data
}

export async function deleteAccount(confirm) {
  await request('DELETE', '/auth/me/', { confirm })
  setToken(null)
}
