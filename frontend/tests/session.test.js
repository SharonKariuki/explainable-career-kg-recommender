// How long a sign-in lasts: the token lives in the tab's sessionStorage only.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { runnerImport } from 'vite'

function storage(initial = {}) {
  const items = new Map(Object.entries(initial))
  return {
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => items.set(key, String(value)),
    removeItem: (key) => items.delete(key),
  }
}

const KEY = 'ajiraguide.token'
const local = storage({ [KEY]: 'saved-by-the-old-version', theme: 'dark' })
const session = storage()
Object.defineProperty(globalThis, 'localStorage', { value: local, configurable: true })
Object.defineProperty(globalThis, 'sessionStorage', { value: session, configurable: true })

const root = fileURLToPath(new URL('..', import.meta.url))
const api = (await runnerImport('./src/api.js', { root, logLevel: 'error' })).module

const json = (status, body) => ({ status, ok: status >= 200 && status < 300, json: async () => body })

test('a token saved by the old version is removed and does not sign anyone in', () => {
  assert.equal(local.getItem(KEY), null)
  assert.equal(local.getItem('theme'), 'dark')
  assert.equal(api.getToken(), null)
})

test('signing in keeps the token for the tab only, and signing out removes it', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => json(200, { token: 'abc', username: 'amina' }))
  await api.login('amina', 'secret')
  assert.equal(api.getToken(), 'abc')
  assert.equal(session.getItem(KEY), 'abc')
  assert.equal(local.getItem(KEY), null)

  await api.logout()
  assert.equal(api.getToken(), null)
  assert.equal(session.getItem(KEY), null)
})
