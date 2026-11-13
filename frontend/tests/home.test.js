// Home: the greeting name, plan counts, and the plan and saved tiles with and without data.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { runnerImport } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const load = async (path) => (await runnerImport(path, { root, logLevel: 'error' })).module
const { displayName, planCounts } = await load('./src/format.js')
const { PlanTile, SavedTile } = await load('./src/screens/DashboardScreen.jsx')

const render = (component, props) => renderToStaticMarkup(createElement(component, props))

const PROGRESS = [
  { skill_id: 'a', label: 'NumPy', status: 'done' },
  { skill_id: 'b', label: 'pandas', status: 'learning' },
  { skill_id: 'c', label: 'PyTorch', status: 'learning' },
]

test('the greeting uses the first name, or the username when no name is saved', () => {
  assert.equal(displayName({ username: 'amina', name: 'Amina Otieno' }), 'Amina')
  assert.equal(displayName({ username: 'amina', name: '  ' }), 'amina')
  assert.equal(displayName({ username: 'amina' }), 'amina')
})

test('plan progress is counted by status', () => {
  assert.deepEqual(planCounts(PROGRESS), { learning: 2, done: 1 })
  assert.deepEqual(planCounts([]), { learning: 0, done: 0 })
})

test('the plan tile shows counts and skills, and says which are done', () => {
  const html = render(PlanTile, { progress: PROGRESS })
  assert.match(html, /2 learning · 1 done/)
  assert.match(html, /1 of 3 skills in your plan done/)
  assert.match(html, /NumPy<span class="visually-hidden"> \(done\)/)
  assert.match(html, /href="#\/plan"/)
})

test('an empty plan tile says how to start', () => {
  const html = render(PlanTile, { progress: [] })
  assert.match(html, /Mark a skill as learning or done/)
  assert.doesNotMatch(html, /class="progress/)
})

test('the saved tile lists the latest three careers with their match', () => {
  const saved = [1, 2, 3, 4].map((n) => ({ career_code: `15-000${n}.00`, title: `Career ${n}`, match: n === 2 ? null : { rank: n } }))
  const html = render(SavedTile, { saved })
  assert.match(html, /4 careers saved/)
  assert.equal(html.match(/class="tile-row"/g).length, 3)
  assert.match(html, /Your match #1/)
  assert.match(html, /Not linked to your skills yet/)
  assert.doesNotMatch(html, /Career 4/)
})

test('an empty saved tile points to the careers list', () => {
  assert.match(render(SavedTile, { saved: [] }), /href="#\/careers"/)
})
