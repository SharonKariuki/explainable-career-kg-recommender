import { useEffect, useState } from 'react'

import { getRecommendations } from '../api.js'
import { EmptyState, Pill, SkillChip, Status } from '../components.jsx'
import { capitalise, fitLabel } from '../format.js'
import { Icon } from '../icons.jsx'

// The skills screen advises three or more skills for better results.
const ADVISED_SKILLS = 3
// Enough for the top match and the few listed under it.
const CAREERS = 4
// Scores run from 0 to 1; the bars show them in tenths.
const TENTHS = 10
const LIST_ROWS = 4
const TOP_SKILLS = 5

function greeting(hour) {
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? '' : 's'}`
}

// The single most useful thing to do next, from the profile as it stands.
function nextStep(skillCount, unsure, top) {
  if (skillCount < ADVISED_SKILLS) {
    return {
      title: `Add ${plural(ADVISED_SKILLS - skillCount, 'more skill')}.`,
      text: 'Three or more skills give better results.',
      action: { href: '#/assessment', label: 'Add skills' },
    }
  }
  if (unsure.length === 1) {
    return {
      title: `Reword “${unsure[0]}”.`,
      text: 'It had no close match in our data, so it counts for less in your matches.',
      action: { href: '#/assessment', label: 'Edit skills' },
    }
  }
  if (unsure.length) {
    return {
      title: `Reword ${plural(unsure.length, 'uncertain skill')}.`,
      text: `${unsure.map((q) => `“${q}”`).join(', ')} had no close match in our data, so they count for less.`,
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

// A score as ten segments; any score above zero fills at least one.
function ScoreBar({ score }) {
  const filled = score > 0 ? Math.max(1, Math.round(score * TENTHS)) : 0
  return (
    <span className="seg-bar" aria-hidden="true">
      {Array.from({ length: TENTHS }, (_, i) => <i key={i} className={i < filled ? 'on' : ''} />)}
    </span>
  )
}

export default function DashboardScreen({ user }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [hello] = useState(() => greeting(new Date().getHours()))

  useEffect(() => {
    let current = true
    getRecommendations(CAREERS)
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
            ? 'The career that fits your skills best, what else fits, and what to do next.'
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
  const unsure = data.matches.filter((m) => m.low_confidence).map((m) => m.query)
  const uncertain = unsure.length
  const [top, ...others] = data.recommendations
  const next = nextStep(skillCount, unsure, top)
  // Uncertain skills first: they are the ones worth acting on.
  const skillRows = [...data.matches].sort((a, b) => b.low_confidence - a.low_confidence).slice(0, LIST_ROWS)

  // One tile per question: what fits best, what to do next, what else fits, and how the profile reads.
  return (
    <div className="dash-panel">
      {band}
      <div className="dash">
        <section className="tile glassy t-match" aria-labelledby="match-label">
          <div className="tile-head spread">
            <div className="tile-head">
              <i className="tile-icon"><Icon name="graph" /></i>
              <h2 id="match-label">Your top match</h2>
            </div>
            {top && <Pill tone={top.fit === 'strong' ? 'match' : 'neutral'}>{fitLabel(top.fit)}</Pill>}
          </div>
          {top ? (
            <>
              <div>
                <p className="match-title">{top.title}</p>
                <p className="sub num">
                  {capitalise(top.domain)}
                  {top.matched_skills.length > 0 && ` · uses ${top.matched_skills.length} of your ${plural(skillCount, 'skill')}`}
                </p>
              </div>
              {top.matched_skills.length > 0 && (
                <ul className="chips skill-chips">
                  {top.matched_skills.slice(0, TOP_SKILLS).map((s) => <SkillChip key={s.skill_id} skill={s} />)}
                </ul>
              )}
              <div className="match-foot">
                <span className="match-score">
                  <b className="figure small num">{top.score.toFixed(2)}</b>
                  <ScoreBar score={top.score} />
                  <span className="sub">match score, 0 to 1</span>
                </span>
                <a className="tile-tag" href={`#/careers/${top.career_code}`}>See why it fits</a>
              </div>
            </>
          ) : (
            <p className="muted">None of your skills matched a career yet. Try rewording them.</p>
          )}
        </section>

        <section className="hero-card dash-callout t-next" aria-labelledby="next-label">
          <p className="mono" id="next-label"><i aria-hidden="true" />Next step</p>
          <h2>{next.title}</h2>
          <p className="hero-sub">{next.text}</p>
          <a className="btn small band-solid" href={next.action.href}>{next.action.label}</a>
        </section>

        <section className="tile t-more" aria-labelledby="more-label">
          <div className="tile-head spread">
            <div>
              <h2 id="more-label">What else fits</h2>
              <p className="sub">Your next matches; scores run from 0 to 1</p>
            </div>
            <a className="tile-tag" href="#/recommendations">See all</a>
          </div>
          {others.length ? (
            <ol className="tile-list">
              {others.map((r) => (
                <li key={r.career_code}>
                  <a className="tile-row" href={`#/careers/${r.career_code}`}>
                    <span className="av num">{r.rank}</span>
                    <span className="row-main">
                      <b>{r.title}</b>
                      <span className="sub">{capitalise(r.domain)}</span>
                    </span>
                    <ScoreBar score={r.score} />
                    <strong className="num">{r.score.toFixed(2)}</strong>
                  </a>
                </li>
              ))}
            </ol>
          ) : (
            <p className="muted small">No other careers link to your skills yet.</p>
          )}
        </section>

        <section className="tile t-skills" aria-labelledby="skills-label">
          <div className="tile-head spread">
            <div>
              <h2 id="skills-label">Your skills</h2>
              <p className="sub num">
                {plural(skillCount, 'skill')} in your profile{uncertain > 0 && ` · ${uncertain} uncertain`}
              </p>
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
    </div>
  )
}
