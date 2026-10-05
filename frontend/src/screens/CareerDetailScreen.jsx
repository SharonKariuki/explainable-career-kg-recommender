import { useEffect, useState } from 'react'

import { getRecommendation } from '../api.js'
import { Meter, Status } from '../components.jsx'
import { requirementLevel, sourceNames } from '../format.js'

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
        <a href="#/recommendations">← All my matches</a>
        <Status loading={!error} error={error} />
      </>
    )
  }

  const c = career.components
  return (
    <>
      <a href="#/recommendations">← All my matches</a>
      <section className="card">
        <p className="muted domain">Match #{career.rank} · {career.domain}</p>
        <h1>{career.title}</h1>

        <h2>Why it suits you</h2>
        <div className="explanation">
          {career.explanation.map((sentence) => <p key={sentence}>{sentence}</p>)}
        </div>

        <h2>Score breakdown</h2>
        <p className="muted">Overall score {career.score.toFixed(2)}, the weighted sum of:</p>
        <div className="meters stacked">
          <Meter label="Coverage: your skills it requires" value={c.coverage} weight={career.weights.coverage} />
          <Meter label="Similarity: your skills vs. the role description" value={c.profile_similarity} weight={career.weights.profile_similarity} />
          <Meter label="Proximity: closeness in the skills graph" value={c.graph_proximity} weight={career.weights.graph_proximity} />
        </div>
      </section>

      <section className="card">
        <h2>Your skills this career uses</h2>
        {career.skill_contributions.length ? (
          <table>
            <thead>
              <tr><th>You said</th><th>Matched skill</th><th>For this career</th></tr>
            </thead>
            <tbody>
              {career.skill_contributions.map((s) => (
                <tr key={s.skill_id}>
                  <td>{s.query}</td>
                  <td>
                    {s.skill_label}
                    {s.low_confidence && <span className="tag warn">uncertain</span>}
                  </td>
                  <td>{requirementLevel(s.edge_weight)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="empty">This career does not directly require any of your listed skills.</p>
        )}
      </section>

      <section className="card">
        <h2>Skills to build</h2>
        <p className="muted">What this career needs that you did not list, most important first.</p>
        <ol className="gap">
          {career.skills_gap.map((g) => (
            <li key={g.skill_id}>
              <span className="gap-skill">{g.label}</span>
              <span className="tag">{requirementLevel(g.edge_weight)}</span>
              <span className="muted source">{sourceNames(g.sources)}</span>
            </li>
          ))}
        </ol>
      </section>
    </>
  )
}
