// The history screen: rank movement labels and the stored snapshot as shown.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { runnerImport } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const { RunDetail } = (await runnerImport('./src/screens/HistoryScreen.jsx', { root, logLevel: 'error' })).module
const { movement } = (await runnerImport('./src/format.js', { root, logLevel: 'error' })).module

test('movement compares with the previous snapshot', () => {
  assert.deepEqual(movement(1, 3), { label: 'Up 2', tone: 'ok' })
  assert.deepEqual(movement(4, 2), { label: 'Down 2', tone: 'warn' })
  assert.deepEqual(movement(2, 2), { label: 'Same place', tone: 'neutral' })
  assert.deepEqual(movement(5, null), { label: 'New', tone: 'ok' })
})

test('a snapshot shows each career with its movement, explanation and gaps', () => {
  const run = {
    created_at: '2026-11-12T08:00:00Z', skills: ['Python', 'statistics'], background: '', previous_id: 3,
    recommendations: [{
      rank: 1, previous_rank: 2, career_code: '15-2051.00', title: 'Data Scientists', domain: 'data',
      score: 0.61, fit: 'strong', explanation: ['Data Scientists is a strong match for your skills (score 0.61).'],
      skill_gaps: [{ label: 'machine learning', requirement: 'Core requirement' }],
    }],
  }
  const html = renderToStaticMarkup(createElement(RunDetail, { run }))
  for (const text of ['Data Scientists', 'Up 1', 'score 0.61', 'Skills to build: machine learning', 'Python']) {
    assert.ok(html.includes(text), text)
  }
})
