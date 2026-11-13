// The sign-in forms follow the address, and the welcome page greets a new student.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { runnerImport } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const load = async (path) => (await runnerImport(path, { root, logLevel: 'error' })).module
const AuthScreen = (await load('./src/screens/AuthScreen.jsx')).default
const WelcomeScreen = (await load('./src/screens/WelcomeScreen.jsx')).default

const render = (component, props) => renderToStaticMarkup(createElement(component, props))

test('the sign-in address shows the sign-in form', () => {
  const html = render(AuthScreen, { mode: 'login', onSignedIn() {} })
  assert.match(html, /<h1>Sign in<\/h1>/)
  assert.match(html, /autoComplete="current-password"|autocomplete="current-password"/)
  assert.doesNotMatch(html, /Full name/)
  assert.match(html, /Create an account/)
})

test('the sign-up address shows the account form with its optional fields', () => {
  const html = render(AuthScreen, { mode: 'register', onSignedIn() {} })
  assert.match(html, /<h1>Create your account<\/h1>/)
  assert.match(html, /Full name/)
  assert.match(html, /autocomplete="new-password"/i)
  assert.match(html, /Already have an account\?/)
})

test('a session notice shows on the sign-in form', () => {
  assert.match(render(AuthScreen, { mode: 'login', onSignedIn() {}, notice: 'Your session has ended.' }), /Your session has ended\./)
})

test('the welcome page greets by first name and leads to the profile', () => {
  const html = render(WelcomeScreen, { user: { username: 'amina', name: 'Amina Otieno' } })
  assert.match(html, /Welcome, Amina/)
  assert.equal(html.match(/<li /g).length, 3)
  assert.match(html, /href="#\/profile"[^>]*>Add your skills/)
})
