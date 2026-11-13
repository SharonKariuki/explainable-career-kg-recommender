// Regression tests for the matches list and career page, rendered to HTML on
// the server from a fixture the real engine produced (see fixtures/).
// Run with `npm test`.

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { runnerImport } from 'vite'

const fixture = JSON.parse(readFileSync(new URL('./fixtures/recommendations.json', import.meta.url), 'utf-8'))

async function load(path) {
  return (await runnerImport(path, { root: fileURLToPath(new URL('..', import.meta.url)), logLevel: 'error' })).module
}

const { MatchCard, SkillReading } = await load('./src/screens/RecommendationsScreen.jsx')
const { MatchDetail } = await load('./src/screens/CareerDetailScreen.jsx')

const render = (component, props) => renderToStaticMarkup(createElement(component, props))
const text = (html) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')

function detail(changes = {}) {
  return render(MatchDetail, { career: { ...fixture.detail, ...changes } })
}

test('a match card shows the label, score and reason without the score components', () => {
  const match = fixture.recommendations[0]
  const html = render(MatchCard, { match })
  assert.match(text(html), /Good match/)
  assert.match(text(html), new RegExp(`Match score ${match.score.toFixed(2)}`))
  assert.ok(text(html).includes(match.reason))
  assert.doesNotMatch(text(html), /Coverage|Similarity|Proximity|%/)
})

test('a match card labels its rank and lists the matched skills', () => {
  const match = fixture.recommendations[0]
  const html = render(MatchCard, { match })
  assert.match(html, /<span class="visually-hidden">Rank <\/span>1/)
  assert.match(html, /<ul class="chips skill-chips" aria-label="Your skills this career uses">/)
  for (const s of match.matched_skills) assert.ok(text(html).includes(s.label))
})

test('an uncertain skill is marked in words on the card', () => {
  const match = structuredClone(fixture.recommendations[0])
  match.matched_skills[0].low_confidence = true
  assert.match(text(render(MatchCard, { match })), /unsure match/)
})

test('uncertain skill readings are named outside the collapsed list', () => {
  const html = render(SkillReading, { matches: fixture.matches })
  const visible = text(html.slice(0, html.indexOf('<details')))
  assert.match(visible, /“playing guitar” was read as/)
})

test('the career page leads with the match and uses real headings', () => {
  const html = detail()
  assert.match(html, /<section class="hero-card" aria-labelledby="match-heading">/)
  for (const heading of ['Why it suits you', 'Skills you already have', 'Skills to develop']) {
    assert.match(html, new RegExp(`<h2[^>]*>(<i[^>]*></i>)?${heading}</h2>`))
  }
  assert.ok(html.indexOf('Skills you already have') < html.indexOf('How this match was calculated'))
})

test('three skills to develop come first and the rest keep their order', () => {
  const html = detail()
  const before = text(html.slice(0, html.indexOf('Show 7 more')))
  const gap = fixture.detail.skills_gap.map((g) => g.label)
  for (const label of gap.slice(0, 3)) assert.ok(before.includes(label))
  for (const label of gap.slice(3)) assert.ok(!before.includes(label))
  const order = gap.map((label) => html.indexOf(`<b>${label}</b>`))
  assert.deepEqual(order, [...order].sort((a, b) => a - b))
  assert.match(html, /<span class="visually-hidden">Priority <\/span>4/)
})

test('the technical evidence is kept, collapsed, with the score limitations', () => {
  const html = detail()
  const technical = html.slice(html.indexOf('<details class="disclosure technical"'))
  assert.match(html, /<details class="disclosure technical" id="how-calculated">/)
  for (const sentence of fixture.detail.explanation) assert.ok(text(technical).includes(sentence))
  assert.match(text(technical), /not a percentage/)
  assert.match(technical, /Coverage: .*weight 70%/)
  assert.match(technical, /Similarity: .*weight 10%/)
  assert.match(technical, /Proximity: .*weight 20%/)
  assert.match(technical, /<svg[^>]+role="img"/)
  assert.match(text(technical), /O\*NET|ESCO/)
})

test('an uncertain skill stays visible outside the technical section', () => {
  const skills = structuredClone(fixture.detail.skill_contributions)
  skills[0].low_confidence = true
  const html = detail({ skill_contributions: skills })
  const visible = text(html.slice(0, html.indexOf('<details class="disclosure technical"')))
  assert.match(visible, new RegExp(`Unsure match for your “${skills[0].query}”`))
})

test('a match card shows the evidence-limited label when the API limits it', () => {
  const match = { ...fixture.recommendations[0], fit: 'strong', fit_shown: 'possible' }
  const html = text(render(MatchCard, { match }))
  assert.match(html, /Possible match/)
  assert.doesNotMatch(html, /Strong match/)
})

test('a match card falls back to the fit label for responses without fit_shown', () => {
  const match = { ...fixture.recommendations[0], fit: 'good' }
  delete match.fit_shown
  assert.match(text(render(MatchCard, { match })), /Good match/)
})

test('the career page headline uses the shown label', () => {
  assert.match(text(detail({ fit: 'strong', fit_shown: 'possible' })), /Possible match/)
})
