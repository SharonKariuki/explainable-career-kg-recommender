// The careers list: which filter an address asks for, and what each filter keeps.
// Run with `npm test`.

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { runnerImport } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const { filterCareers, showFilter } = (await runnerImport('./src/format.js', { root, logLevel: 'error' })).module

const CAREERS = [
  { career_code: '1', title: 'Data Scientists', description: 'Analyse data.', domain: 'data science', match: { rank: 1 }, saved: true },
  { career_code: '2', title: 'Web Developers', description: 'Build sites.', domain: 'software engineering', match: null, saved: true },
  { career_code: '3', title: 'Statisticians', description: 'Model data.', domain: 'data science', match: { rank: 2 }, saved: false },
]
const codes = (careers) => careers.map((c) => c.career_code)

test('the address chooses the filter, and an unknown value means all', () => {
  assert.equal(showFilter('saved'), 'saved')
  assert.equal(showFilter('matched'), 'matched')
  assert.equal(showFilter(undefined), 'all')
  assert.equal(showFilter('nonsense'), 'all')
})

test('each filter keeps the right careers', () => {
  assert.deepEqual(codes(filterCareers(CAREERS, 'all', 'all', '')), ['1', '2', '3'])
  assert.deepEqual(codes(filterCareers(CAREERS, 'saved', 'all', '')), ['1', '2'])
  assert.deepEqual(codes(filterCareers(CAREERS, 'matched', 'all', '')), ['1', '3'])
})

test('the filter combines with the domain and the search', () => {
  assert.deepEqual(codes(filterCareers(CAREERS, 'saved', 'data science', '')), ['1'])
  assert.deepEqual(codes(filterCareers(CAREERS, 'all', 'all', 'model')), ['3'])
  assert.deepEqual(codes(filterCareers(CAREERS, 'matched', 'software engineering', '')), [])
})
