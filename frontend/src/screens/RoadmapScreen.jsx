import { useEffect, useState } from 'react'

import { getRecommendation, getRecommendations } from '../api.js'
import { EmptyState, Notice, PageHeader, Pill, Status } from '../components.jsx'
import { capitalise, sourceNames } from '../format.js'
import { Icon } from '../icons.jsx'
import { navigate } from '../router.js'

// The API caps top at 50, above the number of careers, so every ranked career can be picked.
const ALL_CAREERS = 50

export default function RoadmapScreen({ code }) {
  const [careers, setCareers] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let current = true
    getRecommendations(ALL_CAREERS)
      .then((result) => current && setCareers(result.recommendations))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  const header = <PageHeader title="Skills roadmap" subtitle="What you already bring to a career, and what to build next." />

  if (!careers) return <>{header}<Status loading={!error} error={error} /></>

  if (!careers.length) {
    return (
      <>
        {header}
        <EmptyState title="No careers to plan for yet" action={{ href: '#/assessment', label: 'Add your skills' }}>
          A roadmap needs a career that uses at least one of your skills.
        </EmptyState>
      </>
    )
  }

  const selected = code || careers[0].career_code

  return (
    <>
      {header}
      <label className="select glass">
        <span className="visually-hidden">Career</span>
        <select value={selected} onChange={(e) => navigate(`/roadmap/${e.target.value}`)}>
          {/* A career outside the ranking still shows, so the select matches the address. */}
          {!careers.some((c) => c.career_code === selected) && <option value={selected}>{selected}</option>}
          {careers.map((c) => (
            <option key={c.career_code} value={c.career_code}>{c.rank}. {c.title}</option>
          ))}
        </select>
        <Icon name="chevron" />
      </label>
      <RoadmapDetail key={selected} code={selected} />
    </>
  )
}

function RoadmapDetail({ code }) {
  const [career, setCareer] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let current = true
    getRecommendation(code)
      .then((result) => current && setCareer(result))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [code])

  if (!career) return <Status loading={!error} error={error} />

  const have = career.skill_contributions
  const gap = career.skills_gap

  return (
    <>
      <section className="card panel roadmap-summary">
        <div className="grow">
          <p className="mono">Match #{career.rank} · {career.domain}</p>
          <h2>{career.title}</h2>
          <p className="muted small num">
            Uses {have.length} of your skills · {gap.length} skills to build shown
          </p>
        </div>
        <a className="btn glass" href={`#/careers/${code}`}>Details</a>
      </section>

      <Notice icon="bulb" title="How skills to build are ordered">
        Skills the career needs most come first; among those, skills distinctive to this career lead over ones nearly
        every career needs.
      </Notice>

      <div className="split-2">
        <section className="card panel">
          <div className="ph">
            <h2>Already in your profile</h2>
            <span className="num">{have.length}</span>
          </div>
          {have.length ? (
            <ul className="list">
              {have.map((s) => (
                <li key={s.skill_id} className="row">
                  <span className="av"><Icon name="check" size={16} /></span>
                  <span className="row-main">
                    <b>{s.skill_label}</b>
                    <span className="sub">You said “{s.query}”</span>
                  </span>
                  <span className="row-value">
                    <Pill>{s.requirement}</Pill>
                    {s.low_confidence && <Pill tone="warn">Uncertain</Pill>}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty">None of your listed skills is required directly.</p>
          )}
        </section>

        <section className="card panel">
          <div className="ph">
            <h2>Skills to develop</h2>
            <span>Highest priority first</span>
          </div>
          {gap.length ? (
            <ol className="list">
              {gap.map((g, i) => (
                <li key={g.skill_id} className="row">
                  <span className="av num" aria-label={`Priority ${i + 1}`}>{i + 1}</span>
                  <span className="row-main">
                    <b>{g.label}</b>
                    <span className="sub">{capitalise(g.skill_type)} · {sourceNames(g.sources)}</span>
                  </span>
                  <span className="row-value"><Pill>{g.requirement}</Pill></span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="empty">Your profile already covers every skill this career requires.</p>
          )}
        </section>
      </div>
    </>
  )
}
