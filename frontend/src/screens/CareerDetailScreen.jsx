import { useEffect, useState } from 'react'

import { getRecommendation } from '../api.js'
import CareerGraph from '../CareerGraph.jsx'
import { Meter, PageHeader, Pill, Status } from '../components.jsx'
import { capitalise, sourceNames } from '../format.js'
import { Icon } from '../icons.jsx'

const BACK = { href: '#/recommendations', label: 'All my matches' }

export default function CareerDetailScreen({ code }) {
  const [career, setCareer] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    // App keys this screen by career code, so state starts fresh for each career.
    let current = true
    getRecommendation(code)
      .then((result) => current && setCareer(result))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [code])

  if (!career) {
    return (
      <>
        <PageHeader title="Career" back={BACK} />
        <Status loading={!error} error={error} />
      </>
    )
  }

  const c = career.components
  return (
    <>
      <PageHeader title={career.title} subtitle={`Match #${career.rank} · ${capitalise(career.domain)}`} back={BACK} />

      <div className="button-row">
        <a className="btn glass" href={`#/roadmap/${code}`}><Icon name="roadmap" />Skills roadmap</a>
        <button type="button" className="btn glass" onClick={() => document.getElementById('career-graph').scrollIntoView()}>
          <Icon name="graph" />Skills graph
        </button>
      </div>

      <section className="card panel">
        <p className="mono">Why it suits you</p>
        <div className="explanation">
          {career.explanation.map((sentence) => <p key={sentence}>{sentence}</p>)}
        </div>
      </section>

      <section className="card panel" id="career-graph">
        <div className="ph"><h2>Skills graph</h2></div>
        <CareerGraph career={career} />
      </section>

      <section className="card panel">
        <div className="ph">
          <h2>Score breakdown</h2>
          <span className="num">Overall {career.score.toFixed(2)}</span>
        </div>
        <p className="muted small">The overall score is the weighted sum of:</p>
        <div className="meters stacked">
          <Meter label="Coverage: your skills it requires" value={c.coverage} weight={career.weights.coverage} />
          <Meter label="Similarity: your skills vs. the role description" value={c.profile_similarity} weight={career.weights.profile_similarity} />
          <Meter label="Proximity: closeness in the skills graph" value={c.graph_proximity} weight={career.weights.graph_proximity} />
        </div>
      </section>

      <div className="split-2">
        <section className="card panel">
          <div className="ph">
            <h2>Your skills this career uses</h2>
            <span className="num">{career.skill_contributions.length}</span>
          </div>
          {career.skill_contributions.length ? (
            <ul className="list">
              {career.skill_contributions.map((s) => (
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
            <p className="empty">This career does not directly require any of your listed skills.</p>
          )}
        </section>

        <section className="card panel">
          <div className="ph">
            <h2>Skills to build</h2>
            <a href={`#/roadmap/${code}`}>Roadmap</a>
          </div>
          <p className="muted small">What this career needs that you did not list, most important first.</p>
          <ol className="list">
            {career.skills_gap.map((g, i) => (
              <li key={g.skill_id} className="row">
                <span className="av num">{i + 1}</span>
                <span className="row-main">
                  <b>{g.label}</b>
                  <span className="sub">{sourceNames(g.sources)}</span>
                </span>
                <span className="row-value"><Pill>{g.requirement}</Pill></span>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </>
  )
}
