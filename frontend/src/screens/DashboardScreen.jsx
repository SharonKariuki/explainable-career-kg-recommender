import { useEffect, useState } from 'react'

import { getProgress, getRecommendations, getSaved } from '../api.js'
import { EmptyState, Pill, Progress, ScoreBar, SkillChip, Status } from '../components.jsx'
import { capitalise, displayName, fitLabel, planCounts } from '../format.js'
import { Icon } from '../icons.jsx'

// The skills screen advises three or more skills for better results.
const ADVISED_SKILLS = 3
// Enough for the top match and the few listed under it.
const CAREERS = 4
const LIST_ROWS = 4
const TOP_SKILLS = 5
const SAVED_ROWS = 3
const PLAN_CHIPS = 6

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
      action: { href: '#/profile', label: 'Add skills' },
    }
  }
  if (unsure.length === 1) {
    return {
      title: `Reword “${unsure[0]}”.`,
      text: 'It had no close match in our data, so it counts for less in your matches.',
      action: { href: '#/profile', label: 'Edit skills' },
    }
  }
  if (unsure.length) {
    return {
      title: `Reword ${plural(unsure.length, 'uncertain skill')}.`,
      text: `${unsure.map((q) => `“${q}”`).join(', ')} had no close match in our data, so they count for less.`,
      action: { href: '#/profile', label: 'Edit skills' },
    }
  }
  if (!top) {
    return {
      title: 'No careers linked yet.',
      text: 'None of your skills matched a career. Try rewording them.',
      action: { href: '#/profile', label: 'Edit skills' },
    }
  }
  return {
    title: `See what to learn for ${top.title}.`,
    text: 'Your top match, with the skills it needs that you have not listed.',
    action: { href: `#/plan/${top.career_code}`, label: 'Open plan' },
  }
}

// The amber disc that marks a main action, as on the landing site's primary button.
function ArrowDisc() {
  return <span className="arrow-disc" aria-hidden="true"><Icon name="forward" size={13} /></span>
}

// Skills marked on any career's plan: how many are under way and how many are finished.
export function PlanTile({ progress }) {
  const { learning, done } = planCounts(progress)
  return (
    <section className="tile t-plan" aria-labelledby="plan-label">
      <div className="tile-head spread">
        <div>
          <h2 id="plan-label">My plan</h2>
          <p className="sub num">
            {progress.length ? `${learning} learning · ${done} done` : 'Skills you are building towards a career'}
          </p>
        </div>
        <a className="tile-tag" href="#/plan">Open plan</a>
      </div>
      {progress.length ? (
        <>
          <Progress value={done / progress.length} tone="amber" label={`${done} of ${plural(progress.length, 'skill')} in your plan done`} />
          <ul className="chips">
            {progress.slice(0, PLAN_CHIPS).map((p) => (
              <li key={p.skill_id} className="chip tag">
                {p.status === 'done' && <Icon name="check" size={13} />}
                {p.label}
                <span className="visually-hidden">{p.status === 'done' ? ' (done)' : ' (learning)'}</span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="muted small">Mark a skill as learning or done on a career's plan and it will show here.</p>
      )}
    </section>
  )
}

// The careers saved most recently, each with the user's match where there is one.
export function SavedTile({ saved }) {
  return (
    <section className="tile t-saved" aria-labelledby="saved-label">
      <div className="tile-head spread">
        <div>
          <h2 id="saved-label">Saved careers</h2>
          <p className="sub num">{saved.length ? `${plural(saved.length, 'career')} saved` : 'Careers you want to come back to'}</p>
        </div>
        <a className="tile-tag" href="#/saved">See all</a>
      </div>
      {saved.length ? (
        <ul className="tile-list">
          {saved.slice(0, SAVED_ROWS).map((c) => (
            <li key={c.career_code}>
              <a className="tile-row" href={`#/careers/${c.career_code}`}>
                <span className="av"><Icon name="bookmark" size={16} /></span>
                <span className="row-main">
                  <b>{c.title}</b>
                  <span className="sub">{c.match ? `Your match #${c.match.rank}` : 'Not linked to your skills yet'}</span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted small">Nothing saved yet. <a href="#/careers">Browse careers</a> and save the ones you like.</p>
      )}
    </section>
  )
}

export default function DashboardScreen({ user }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [hello] = useState(() => greeting(new Date().getHours()))

  useEffect(() => {
    let current = true
    Promise.all([getRecommendations(CAREERS), getSaved(), getProgress()])
      .then(([result, saved, progress]) => current && setData({ ...result, saved: saved.careers, progress: progress.skills }))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  const ready = data && data.skills.length > 0

  const band = (
    <header className="dash-band">
      <div className="grow">
        <h1>{hello}, <span className="amber-text">{displayName(user)}</span>.</h1>
        <p>
          {ready
            ? 'The career that fits your skills best, what else fits, and what to do next.'
            : 'Tell AjiraGuide what you can do and it will rank the tech careers that fit.'}
        </p>
      </div>
      {ready && (
        <div className="band-buttons">
          <a className="btn band-ghost" href="#/profile">Edit skills</a>
          <a className="btn band-solid" href="#/matches">See matches<ArrowDisc /></a>
        </div>
      )}
    </header>
  )

  if (!data) return <div className="dash-panel">{band}<Status loading={!error} error={error} /></div>

  if (!ready) {
    return (
      <div className="dash-panel">
        {band}
        <EmptyState title="Start with your skills" action={{ href: '#/profile', label: 'Add your skills' }}>
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
              <h2 id="match-label">Your top match<i className="spark" aria-hidden="true" /></h2>
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
                  <ScoreBar score={top.score} tone="amber" />
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
          <a className="btn small band-solid" href={next.action.href}>{next.action.label}<ArrowDisc /></a>
        </section>

        <section className="tile t-more" aria-labelledby="more-label">
          <div className="tile-head spread">
            <div>
              <h2 id="more-label">What else fits</h2>
              <p className="sub">Your next matches, by how well they fit</p>
            </div>
            <a className="tile-tag" href="#/matches">See all</a>
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
                    <Pill tone={r.fit === 'strong' ? 'match' : 'neutral'}>{fitLabel(r.fit)}</Pill>
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
            <a className="tile-tag" href="#/profile">Edit</a>
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

        <PlanTile progress={data.progress} />
        <SavedTile saved={data.saved} />
      </div>
    </div>
  )
}
