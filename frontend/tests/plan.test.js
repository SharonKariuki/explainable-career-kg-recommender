// My plan and a career's skills plan: which careers are offered, and how rows and lists read.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { runnerImport } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const load = async (path) => (await runnerImport(path, { root, logLevel: 'error' })).module
const { planCareers, statusMap } = await load('./src/format.js')
const { PlanRow } = await load('./src/CareerPlan.jsx')
const { CareersToPlan, SkillsInProgress } = await load('./src/screens/PlanScreen.jsx')

const render = (component, props) => renderToStaticMarkup(createElement(component, props))

const SAVED = [
  { career_code: 'b', title: 'Statisticians', domain: 'data science', match: { rank: 3 } },
  { career_code: 'x', title: 'Web Developers', domain: 'software engineering', match: null },
]
const RANKED = [
  { career_code: 'a', title: 'Data Scientists', domain: 'data science', rank: 1 },
  { career_code: 'b', title: 'Statisticians', domain: 'data science', rank: 3 },
]

test('careers to plan for are the saved ones, then top matches not already listed', () => {
  const careers = planCareers(SAVED, RANKED)
  assert.deepEqual(careers.map((c) => c.career_code), ['b', 'x', 'a'])
  assert.deepEqual(careers.map((c) => c.rank), [3, null, 1])
  assert.deepEqual(careers.map((c) => c.saved), [true, true, false])
  assert.deepEqual(planCareers([], []), [])
})

test('stored progress maps each skill to its status', () => {
  assert.deepEqual(statusMap([{ skill_id: 'a', status: 'done' }, { skill_id: 'b', status: 'learning' }]), { a: 'done', b: 'learning' })
})

test('each career links to its skills plan and says whether it is a match', () => {
  const html = render(CareersToPlan, { careers: planCareers(SAVED, RANKED) })
  assert.match(html, /href="#\/careers\/b\/plan"/)
  assert.match(html, /Match #3/)
  assert.match(html, /Not a match yet/)
  assert.equal(html.match(/>Saved</g).length, 2)
})

test('skills in progress are counted and each has its status control', () => {
  const progress = [
    { skill_id: 'a', label: 'NumPy', status: 'done' },
    { skill_id: 'b', label: 'pandas', status: 'learning' },
  ]
  const html = render(SkillsInProgress, { progress, busy: null, onStatus() {} })
  assert.match(html, /1 learning · 1 done/)
  assert.equal(html.match(/role="radiogroup"/g).length, 2)
  assert.match(html, /aria-label="Progress on NumPy"/)
})

test('a plan row marks the chosen status, and only a finished skill can join the profile', () => {
  const skill = { skill_id: 'a', label: 'NumPy', skill_type: 'tool', requirement: 'Core requirement' }
  const learning = render(PlanRow, { skill, position: 2, status: 'learning', busy: false, onStatus() {}, onAdd() {} })
  assert.match(learning, /aria-checked="true"[^>]*>Learning/)
  assert.match(learning, /aria-label="Priority 2"/)
  assert.doesNotMatch(learning, /Add to my skills/)
  const done = render(PlanRow, { skill, position: 2, status: 'done', busy: false, onStatus() {}, onAdd() {} })
  assert.match(done, /Add to my skills/)
})
