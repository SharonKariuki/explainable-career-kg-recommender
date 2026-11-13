// The skills plan as a roadmap: how skills group into stages, where boxes go, and how nodes read.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { runnerImport } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const load = async (path) => (await runnerImport(path, { root, logLevel: 'error' })).module
const { layoutRoadmap, roadmapSections } = await load('./src/roadmap.js')
const { default: Roadmap } = await load('./src/Roadmap.jsx')

const HAVE = [{ skill_id: 'py', skill_label: 'Python', query: 'python', requirement: 'Core requirement' }]
const GAP = [
  { skill_id: 'sql', label: 'SQL', skill_type: 'tool', requirement: 'Core requirement' },
  { skill_id: 'stats', label: 'Statistics', skill_type: 'knowledge', requirement: 'Core requirement' },
  { skill_id: 'ml', label: 'Machine learning', skill_type: 'knowledge', requirement: 'Important' },
  { skill_id: 'odd', label: 'Something new', skill_type: 'skill', requirement: 'Unheard of' },
]
const sections = roadmapSections(HAVE, GAP, { sql: 'done', ml: 'learning' })

const overlap = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h

test('skills group into stages in order, tools to the right, with their status', () => {
  assert.deepEqual(sections.map((s) => s.key), ['have', 'core', 'important', 'supporting'])
  const core = sections[1]
  assert.deepEqual(core.skills.map((s) => [s.id, s.side, s.state]), [['sql', 'right', 'done'], ['stats', 'left', 'todo']])
  assert.equal(core.done, 1)
  assert.equal(sections[0].done, 1)
  assert.equal(sections[2].skills[0].state, 'learning')
  assert.deepEqual(sections[3].skills.map((s) => s.id), ['odd'])
})

test('stages with no skills are left out', () => {
  assert.deepEqual(roadmapSections([], GAP.slice(2, 3)).map((s) => s.key), ['important'])
  assert.deepEqual(roadmapSections([], []), [])
})

test('boxes never overlap and stay on the canvas, wide or narrow', () => {
  for (const width of [900, 700, 360]) {
    const layout = layoutRoadmap(sections, width)
    assert.equal(layout.compact, width < 640)
    assert.equal(layout.boxes.filter((b) => b.kind === 'skill').length, 5)
    assert.equal(layout.branches.length, 5)
    layout.boxes.forEach((a, i) => {
      assert.ok(a.x >= 0 && a.x + a.w <= layout.width && a.y >= 0 && a.y + a.h <= layout.height, `${a.key} is on the canvas at ${width}`)
      layout.boxes.slice(i + 1).forEach((b) => assert.ok(!overlap(a, b), `${a.key} and ${b.key} overlap at ${width}`))
    })
  }
})

test('stages run down the page in order', () => {
  const ys = layoutRoadmap(sections, 900).boxes.filter((b) => b.kind === 'topic').map((b) => b.y)
  assert.deepEqual(ys, [...ys].sort((a, b) => a - b))
})

test('every skill is a button that says where the student is with it', () => {
  const html = renderToStaticMarkup(createElement(Roadmap, { title: 'Data Scientists', sections, busy: null, onStatus() {}, onAdd() {} }))
  assert.match(html, /Data Scientists/)
  assert.equal(html.match(/<button/g).length, 5)
  assert.match(html, /aria-label="Python, in your profile"/)
  assert.match(html, /aria-label="SQL, done"/)
  assert.match(html, /aria-label="Machine learning, learning"/)
  assert.match(html, /Core requirements<\/span><span[^>]*aria-label="1 of 2 done"/)
  assert.match(html, /Ready for this career/)
})

test('a plan with nothing left to build says so', () => {
  const html = renderToStaticMarkup(createElement(Roadmap, { title: 'Data Scientists', sections: roadmapSections(HAVE, []), busy: null, onStatus() {}, onAdd() {} }))
  assert.match(html, /You cover every required skill/)
})
