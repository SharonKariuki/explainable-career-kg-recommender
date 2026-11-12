// Error messages from the API client, and its retries while the backend starts.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { runnerImport } from 'vite'

async function load(path) {
  return (await runnerImport(path, { root: fileURLToPath(new URL('..', import.meta.url)), logLevel: 'error' })).module
}

const api = await load('./src/api.js')

const json = (status, body) => ({ status, ok: status >= 200 && status < 300, json: async () => body })

test('validation errors name the field and keep every message', () => {
  const error = new api.ApiError(400, { password: ['This password is too short.', 'This password is too common.'] })
  assert.equal(error.message, 'Password: This password is too short. Password: This password is too common.')
})

test('general validation errors are shown without a field name', () => {
  const error = new api.ApiError(400, { non_field_errors: ['Incorrect username or password.'] })
  assert.equal(error.message, 'Incorrect username or password.')
})

test('nested list errors keep the field name', () => {
  const error = new api.ApiError(400, { skills: { 0: ['Ensure this field has no more than 100 characters.'] } })
  assert.equal(error.message, 'Skills: Ensure this field has no more than 100 characters.')
})

test('server, session and missing-page errors read as plain sentences', () => {
  assert.match(new api.ApiError(500, null).message, /went wrong on our side/)
  assert.match(new api.ApiError(401, { detail: 'Invalid token.' }).message, /session has ended/)
  assert.match(new api.ApiError(404, null).message, /couldn't find that/)
  assert.equal(new api.ApiError(404, { detail: 'That career is not among your recommendations.' }).message,
    'That career is not among your recommendations.')
  assert.doesNotMatch(new api.ApiError(418, null).message, /Request failed/)
})

test('a lost connection says so', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('Failed to fetch') })
  await assert.rejects(api.me(), { message: api.OFFLINE_MESSAGE, status: 0 })
})

test('requests wait while the backend starts, then succeed', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const answers = [json(503, { error: 'App port is not ready' }), json(504, null), json(200, { username: 'amina' })]
  const fetch = t.mock.method(globalThis, 'fetch', async () => answers.shift())
  const states = []
  const stop = api.onWaking((waking) => states.push(waking))

  const pending = api.me()
  for (let i = 0; i < 2; i++) {
    await new Promise((resolve) => setImmediate(resolve))
    t.mock.timers.tick(5000)
  }
  assert.deepEqual(await pending, { username: 'amina' })
  stop()
  assert.equal(fetch.mock.callCount(), 3)
  assert.deepEqual(states, [true, true, false])
})
