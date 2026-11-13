// The route table: what each address opens, where old addresses lead, and what counts as not found.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { runnerImport } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const { activeLink, landing, queryOf, resolve } = (await runnerImport('./src/routes.js', { root, logLevel: 'error' })).module

test('every page has an address', () => {
  const pages = {
    '/home': 'home', '/matches': 'matches', '/profile': 'profile', '/careers': 'careers', '/careers/15-2051.00': 'career',
    '/careers/15-2051.00/fit': 'career', '/careers/15-2051.00/plan': 'career', '/plan': 'plan', '/history': 'history', '/history/7': 'history',
    '/settings': 'settings',
  }
  for (const [address, name] of Object.entries(pages)) assert.equal(resolve(address).name, name, address)
})

test('an address carries its parameters', () => {
  assert.deepEqual(resolve('/careers/15-2051.00').params, { code: '15-2051.00', tab: undefined })
  assert.deepEqual(resolve('/careers/15-2051.00/plan').params, { code: '15-2051.00', tab: 'plan' })
  assert.deepEqual(resolve('/history/12').params, { runId: '12' })
})

test('old addresses lead to the new ones', () => {
  const moved = {
    '': '/home', '/': '/home', '/dashboard': '/home', '/recommendations': '/matches', '/assessment': '/profile',
    '/roadmap': '/plan', '/roadmap/15-2051.00': '/careers/15-2051.00/plan', '/plan/15-2051.00': '/careers/15-2051.00/plan', '/saved': '/careers?show=saved',
  }
  for (const [old, target] of Object.entries(moved)) {
    assert.equal(resolve(old).redirect, target, old)
    assert.notEqual(resolve(target).name, 'not-found', target)
  }
})

test('a query and a trailing slash do not change the page', () => {
  assert.equal(resolve('/careers?show=saved').name, 'careers')
  assert.equal(resolve('/matches/').name, 'matches')
  assert.equal(resolve('/roadmap?x=1').redirect, '/plan?x=1')
  assert.deepEqual(queryOf('/careers?show=saved'), { show: 'saved' })
  assert.deepEqual(queryOf('/careers'), {})
})

test('an unknown address is not found', () => {
  for (const address of ['/nope', '/careers/a/b', '/careers/a/plan/x', '/history/abc', '/homes']) {
    assert.equal(resolve(address).name, 'not-found', address)
  }
})

test('signing in opens the address that was asked for, or home', () => {
  assert.equal(landing('/careers/15-2051.00'), '/careers/15-2051.00')
  assert.equal(landing('/'), '/home')
  assert.equal(landing('/recommendations'), '/matches')
  assert.equal(landing('/nope'), '/home')
})

test('a page marks the link it belongs under', () => {
  const links = [{ path: '/home' }, { path: '/careers' }, { path: '/plan' }]
  assert.equal(activeLink('/careers/15-2051.00', links), '/careers')
  assert.equal(activeLink('/plan?x=1', links), '/plan')
  assert.equal(activeLink('/planets', links), null)
  assert.equal(activeLink('/settings', links), null)
})
