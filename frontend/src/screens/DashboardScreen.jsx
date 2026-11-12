import { useEffect, useState } from 'react'

import { getRecommendations } from '../api.js'
import { EmptyState, Pill, Status } from '../components.jsx'
import { capitalise, fitLabel } from '../format.js'
import { Icon } from '../icons.jsx'

// The skills screen advises three or more skills for better results.
const ADVISED_SKILLS = 3
// The API caps top at 50, above the number of careers, so this ranks them all.
const ALL_CAREERS = 50
// Scores run from 0 to 1; the dot chart and the bars show them in tenths.
const TENTHS = 10
const CHART_CAREERS = 12
const LIST_ROWS = 4
// Short axis labels for the domain chart; other domains use their first word.
const SHORT_DOMAIN = { 'artificial intelligence': 'AI', cybersecurity: 'Security' }

function greeting(hour) {
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? '' : 's'}`
}

// A score as filled tenths; any score above zero shows at least one.
function tenths(score) {
  return score > 0 ? Math.max(1, Math.round(score * TENTHS)) : 0
}

// The single most useful thing to do next, from the profile as it stands.
function nextStep(skillCount, uncertain, top) {
  if (skillCount < ADVISED_SKILLS) {
    return {
      title: `Add ${plural(ADVISED_SKILLS - skillCount, 'more skill')}.`,
      text: 'Three or more skills give better results.',
      action: { href: '#/assessment', label: 'Add skills' },
    }
  }
  if (uncertain) {
    return {
      title: `Reword ${plural(uncertain, 'uncertain skill')}.`,
      text: 'They had no close match in our data, so they count for less.',
      action: { href: '#/assessment', label: 'Edit skills' },
    }
  }
  if (!top) {
    return {
      title: 'No careers linked yet.',
      text: 'None of your skills matched a career. Try rewording them.',
      action: { href: '#/assessment', label: 'Edit skills' },
    }
  }
  return {
    title: `See what to learn for ${top.title}.`,
    text: 'Your top match, with the skills it needs that you have not listed.',
    action: { href: `#/roadmap/${top.career_code}`, label: 'Open roadmap' },
  }
}

// Match scores from the weakest career up to the top match, which carries the amber dot.
function ScoreCurve({ scores }) {
  const W = 150
  const H = 60
  const PAD = 7
  const rising = [...scores].reverse()
  const max = Math.max(...rising)
  const points = rising.map((s, i) => [
    PAD + (rising.length > 1 ? i / (rising.length - 1) : 1) * (W - 2 * PAD),
    H - PAD - (s / max) * (H - 2 * PAD),
  ])
  const [endX, endY] = points[points.length - 1]
  return (
    <svg className="score-curve" viewBox={`0 0 ${W} ${H}`} aria-hidden="true" focusable="false">
      {points.length > 1 && <polyline points={points.map((p) => p.join(',')).join(' ')} />}
      <circle className="halo" cx={endX} cy={endY} r="6.5" />
      <circle cx={endX} cy={endY} r="3.5" />
    </svg>
  )
}

// One column of dots per career, in rank order; empty columns keep the grid full.
function DotChart({ careers }) {
  const columns = Array.from({ length: CHART_CAREERS }, (_, i) => careers[i])
  const summary = careers.length
    ? `Match scores of your top ${plural(careers.length, 'career')}, from ${careers[0].score.toFixed(2)} for ` +
      `${careers[0].title} down to ${careers[careers.length - 1].score.toFixed(2)}.`
    : 'No careers to chart yet.'
  return (
    <div className="dot-chart" role="img" aria-label={summary}>
      <div className="dot-axis num" aria-hidden="true"><span>1.0</span><span>0.5</span><span>0</span></div>
      {columns.map((career, i) => {
        const filled = career ? tenths(career.score) : 0
        return (
          <div key={i} className="dot-col" title={career && `${career.title}: ${career.score.toFixed(2)}`}>
            {Array.from({ length: TENTHS }, (_, row) => {
              const level = TENTHS - row
              const state = level > filled ? '' : level === filled ? (i === 0 ? ' cap top' : ' cap') : ' on'
              return <i key={row} className={`dot${state}`} />
            })}
            <span className="dot-label num">{career ? career.rank : ''}</span>
          </div>
        )
      })}
    </div>
  )
}

function ScoreBar({ score }) {
  const filled = tenths(score)
  return (
    <span className="seg-bar" aria-hidden="true">
      {Array.from({ length: TENTHS }, (_, i) => <i key={i} className={i < filled ? 'on' : ''} />)}
    </span>
  )
}

// Linked careers counted per domain, largest first.
function domainCounts(careers) {
  const counts = new Map()
  for (const career of careers) counts.set(career.domain, (counts.get(career.domain) ?? 0) + 1)
  return [...counts].map(([domain, count]) => ({ domain, count })).sort((a, b) => b.count - a.count)
}

// One rounded bar per domain; the top match's domain is hatched and carries the tooltip.
function DomainBars({ careers }) {
  const domains = domainCounts(careers)
  const top = careers[0].domain
  const ceiling = Math.max(2, 2 * Math.ceil(Math.max(...domains.map((d) => d.count)) / 2))
  const summary = `Careers linked to your skills in each field: ${domains.map((d) => `${capitalise(d.domain)} ${d.count}`).join(', ')}. ` +
    `Your top match is in ${capitalise(top)}.`
  return (
    <div className="bar-chart" role="img" aria-label={summary}>
      <div className="bar-axis num" aria-hidden="true"><span>{ceiling}</span><span>{ceiling / 2}</span><span>0</span></div>
      {domains.map((d) => (
        <div key={d.domain} className="bar-col" title={`${capitalise(d.domain)}: ${plural(d.count, 'career')}`}>
          <div className="bar-track">
            <div className={d.domain === top ? 'bar top' : 'bar'} style={{ height: `${(d.count / ceiling) * 100}%` }}>
              {d.domain === top && <span className="bar-tip num">Top match · {d.count}</span>}
            </div>
          </div>
          <span className="bar-label">{SHORT_DOMAIN[d.domain] ?? capitalise(d.domain.split(' ')[0])}</span>
        </div>
      ))}
    </div>
  )
}

export default function DashboardScreen({ user }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [hello] = useState(() => greeting(new Date().getHours()))

  useEffect(() => {
    let current = true
    getRecommendations(ALL_CAREERS)
      .then((result) => current && setData(result))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  const ready = data && data.skills.length > 0

  const band = (
    <header className="dash-band">
      <div className="grow">
        <h1>{hello}, {user.username}.</h1>
        <p>
          {ready
            ? 'A clear view of the careers your skills link to, how strong each match is, and what to learn next.'
            : 'Tell AjiraGuide what you can do and it will rank the tech careers that fit.'}
        </p>
      </div>
      {ready && (
        <div className="band-buttons">
          <a className="btn band-ghost" href="#/assessment">Edit skills</a>
          <a className="btn band-solid" href="#/recommendations">See matches</a>
        </div>
      )}
    </header>
  )

  if (!data) return <div className="dash-panel">{band}<Status loading={!error} error={error} /></div>

  if (!ready) {
    return (
      <div className="dash-panel">
        {band}
        <EmptyState title="Start with your skills" action={{ href: '#/assessment', label: 'Add your skills' }}>
          List what you can already do, in your own words. AjiraGuide ranks the tech careers that use those skills and
          explains each match.
        </EmptyState>
      </div>
    )
  }

  const skillCount = data.skills.length
  const uncertain = data.matches.filter((m) => m.low_confidence).length
  const confident = data.matches.length - uncertain
  const careers = data.recommendations
  const next = nextStep(skillCount, uncertain, careers[0])
  // Uncertain skills first: they are the ones worth acting on.
  const skillRows = [...data.matches].sort((a, b) => b.low_confidence - a.low_confidence).slice(0, LIST_ROWS)

  // Three columns of two tiles each, so a short tile lets the one below tuck up
  // under it. On narrower screens the columns dissolve and the tiles reorder.
  return (
    <div className="dash-panel">
      {band}
      <div className="dash">
        <div className="dash-col">
          <section className="tile glassy t-linked" aria-labelledby="linked-label">
            <div className="tile-head">
              <i className="tile-icon"><Icon name="graph" /></i>
              <h2 id="linked-label">Careers linked to your skills</h2>
            </div>
            <div className="figure-row">
              <div>
                <div className="figure num">{careers.length}</div>
                <p className="sub num">
                  from {plural(skillCount, 'skill')} · {confident} of {data.matches.length} matched confidently
                </p>
              </div>
              {careers.length > 0 && <ScoreCurve scores={careers.map((r) => r.score)} />}
            </div>
          </section>

          <section className="tile t-top" aria-labelledby="top-label">
            <div className="tile-head spread">
              <div>
                <h2 id="top-label">Top matches</h2>
                <p className="sub">How well each career fits your skills</p>
              </div>
              <a className="tile-tag" href="#/recommendations">See all</a>
            </div>
            {careers.length ? (
              <ol className="tile-list">
                {careers.slice(0, LIST_ROWS).map((r) => (
                  <li key={r.career_code}>
                    <a className="tile-row" href={`#/careers/${r.career_code}`}>
                      <span className="row-main">
                        <b>{r.title}</b>
                        <span className="sub">{capitalise(r.domain)}</span>
                      </span>
                      <ScoreBar score={r.score} />
                      <Pill tone={r.fit === 'strong' ? 'match' : 'neutral'}>{fitLabel(r.fit)}</Pill>
                    </a>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="muted small">None of your skills matched a career yet. Try rewording them.</p>
            )}
          </section>
        </div>

        <div className="dash-col">
          <section className="tile glassy t-scores" aria-labelledby="scores-label">
            <div className="tile-head spread">
              <div>
                <h2 className="tile-kicker" id="scores-label">Match score by rank</h2>
                <div className="figure small num">{careers.length ? careers[0].score.toFixed(2) : '0.00'}</div>
              </div>
              <span className="tile-tag">Top {Math.min(careers.length, CHART_CAREERS) || CHART_CAREERS}</span>
            </div>
            <DotChart careers={careers.slice(0, CHART_CAREERS)} />
          </section>

          <section className="tile t-skills" aria-labelledby="skills-label">
            <div className="tile-head spread">
              <div>
                <h2 id="skills-label">Your skills</h2>
                <p className="sub num">{plural(skillCount, 'skill')} in your profile</p>
              </div>
              <a className="tile-tag" href="#/assessment">Edit</a>
            </div>
            <ul className="tile-list">
              {skillRows.map((m) => (
                <li key={m.query} className="tile-row">
                  <span className={m.low_confidence ? 'av unsure' : 'av have'}>
                    <Icon name={m.low_confidence ? 'alert' : 'check'} size={16} />
                  </span>
                  <span className="row-main">
                    <b>{m.query}</b>
                    <span className="sub">{m.low_confidence ? 'Closest' : 'Matched to'} {m.skill}</span>
                  </span>
                  <Pill tone={m.low_confidence ? 'warn' : 'ok'}>{m.low_confidence ? 'Unsure' : 'Matched'}</Pill>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="dash-col">
          <section className="hero-card dash-callout t-next" aria-labelledby="next-label">
            <p className="mono" id="next-label"><i aria-hidden="true" />Next step</p>
            <h2>{next.title}</h2>
            <p className="hero-sub">{next.text}</p>
            <a className="btn small band-solid" href={next.action.href}>{next.action.label}</a>
          </section>

          <section className="tile t-field" aria-labelledby="domain-label">
            <div className="tile-head spread">
              <div>
                <h2 id="domain-label">Careers by field</h2>
                <p className="sub">Linked careers in each field; your top match's field is striped.</p>
              </div>
              <a className="tile-tag" href="#/careers">Explore</a>
            </div>
            {careers.length ? <DomainBars careers={careers} /> : <p className="muted small">No careers linked yet.</p>}
          </section>
        </div>
      </div>
    </div>
  )
}
