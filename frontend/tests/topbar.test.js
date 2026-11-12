// The top bar: which link is marked current, and how the avatar menu's keys move.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { runnerImport } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const { TopBar } = (await runnerImport('./src/TopBar.jsx', { root, logLevel: 'error' })).module
const { menuTarget } = (await runnerImport('./src/menu.js', { root, logLevel: 'error' })).module

const NAV = [
  { path: '/dashboard', label: 'Home', icon: 'home' },
  { path: '/careers', label: 'Explore', icon: 'explore' },
]
const MORE = [{ path: '/saved', label: 'Saved', icon: 'bookmark' }]

function render(active) {
  return renderToStaticMarkup(createElement(TopBar, {
    nav: NAV, more: MORE, active, user: { username: 'amina' }, theme: 'light', onToggleTheme() {}, onSignOut() {},
  }))
}

test('arrow keys wrap around the menu; Home and End jump to its ends', () => {
  assert.equal(menuTarget('ArrowDown', 0, 5), 1)
  assert.equal(menuTarget('ArrowDown', 4, 5), 0)
  assert.equal(menuTarget('ArrowUp', 0, 5), 4)
  assert.equal(menuTarget('Home', 3, 5), 0)
  assert.equal(menuTarget('End', 1, 5), 4)
  assert.equal(menuTarget('a', 1, 5), null)
})

test('only the current main link is marked as the current page', () => {
  const html = render('/careers')
  assert.equal(html.match(/aria-current="page"/g).length, 1)
  assert.match(html, /href="#\/careers"[^>]*aria-current="page"/)
})

test('the avatar menu starts closed and is labelled for the signed-in user', () => {
  const html = render('/saved')
  assert.match(html, /aria-haspopup="menu"/)
  assert.match(html, /aria-expanded="false"/)
  assert.match(html, /Account menu for amina/)
  assert.doesNotMatch(html, /role="menu"/)
  assert.doesNotMatch(html, /aria-current="page"/)  // no pill is current on an account page
})
