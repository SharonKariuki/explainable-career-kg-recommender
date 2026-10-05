import { useEffect, useState } from 'react'

import { getRecommendations } from '../api.js'
import { Meter, Status } from '../components.jsx'

export default function RecommendationsScreen() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let current = true
    getRecommendations(10)
      .then((result) => current && setData(result))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  if (!data) return <Status loading={!error} error={error} />

  if (!data.skills.length) {
    return (
      <section className="card">
        <h1>Your career matches</h1>
        <p className="empty">You have not listed any skills yet.</p>
        <a href="#/profile">Add your skills</a>
      </section>
    )
  }

  const uncertain = data.matches.filter((m) => m.low_confidence)

  return (
    <>
      <section className="card">
        <h1>Your career matches</h1>
        <p className="muted">How we read your skills:</p>
        <ul className="matches">
          {data.matches.map((m) => (
            <li key={m.query} className={m.low_confidence ? 'uncertain' : undefined}>
              <strong>{m.query}</strong>
              {m.query.toLowerCase() !== m.skill.toLowerCase() && <> → {m.skill}</>}
              {m.low_confidence && <span className="tag warn">uncertain</span>}
            </li>
          ))}
        </ul>
        {uncertain.length > 0 && (
          <p className="note">
            Some skills had no close match in our data, so they count for less. Rewording them on{' '}
            <a href="#/profile">your skills</a> page may help.
          </p>
        )}
      </section>

      <ol className="results">
        {data.recommendations.map((r) => (
          <li key={r.career_code} className="card result">
            <div className="result-head">
              <span className="rank">{r.rank}</span>
              <div className="grow">
                <h2>
                  <a href={`#/careers/${r.career_code}`}>{r.title}</a>
                </h2>
                <p className="muted domain">{r.domain}</p>
              </div>
              <span className="score" title="Overall score, 0 to 1">{r.score.toFixed(2)}</span>
            </div>
            <p>{r.summary}</p>
            <div className="meters">
              <Meter label="Coverage" value={r.components.coverage} />
              <Meter label="Similarity" value={r.components.profile_similarity} />
              <Meter label="Proximity" value={r.components.graph_proximity} />
            </div>
            <a href={`#/careers/${r.career_code}`}>Why this career, and what to learn →</a>
          </li>
        ))}
      </ol>
    </>
  )
}
