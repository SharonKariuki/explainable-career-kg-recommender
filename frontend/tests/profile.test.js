// The profile's details form: what it shows, and when there is something to save.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { runnerImport } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const load = async (path) => (await runnerImport(path, { root, logLevel: 'error' })).module
const { accountChanged } = await load('./src/format.js')
const { AccountForm } = await load('./src/AccountForm.jsx')

const ACCOUNT = { username: 'amina', name: 'Amina Otieno', email: 'amina@example.com' }

test('there is something to save only when the name or email differs', () => {
  assert.equal(accountChanged(ACCOUNT, 'Amina Otieno', 'amina@example.com'), false)
  assert.equal(accountChanged(ACCOUNT, ' Amina Otieno ', 'amina@example.com '), false)
  assert.equal(accountChanged(ACCOUNT, 'Amina O.', 'amina@example.com'), true)
  assert.equal(accountChanged(ACCOUNT, 'Amina Otieno', ''), true)
  assert.equal(accountChanged({ username: 'amina' }, '', ''), false)
})

test('the form shows the saved name and email, with nothing to save yet', () => {
  const html = renderToStaticMarkup(createElement(AccountForm, { account: ACCOUNT, onChange() {} }))
  assert.match(html, /value="Amina Otieno"/)
  assert.match(html, /value="amina@example.com"/)
  assert.match(html, /Signed in as amina/)
  assert.match(html, /<button type="submit"[^>]*disabled=""/)
})

test('an account with no name or email shows empty fields', () => {
  const html = renderToStaticMarkup(createElement(AccountForm, { account: { username: 'amina', email: '' }, onChange() {} }))
  assert.equal(html.match(/value=""/g).length, 2)
})
