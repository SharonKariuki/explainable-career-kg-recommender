import { useEffect, useState } from 'react'

import { getSaved } from '../api.js'
import { EmptyState, PageHeader, Pill, SaveButton, Status } from '../components.jsx'
import { capitalise } from '../format.js'
import { Icon } from '../icons.jsx'

export default function SavedScreen() {
  const [careers, setCareers] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let current = true
    getSaved()
      .then((result) => current && setCareers(result.careers))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  const header = <PageHeader title="Saved careers" subtitle="Careers you bookmarked to come back to, newest first." />

  if (!careers) return <>{header}<Status loading={!error} error={error} /></>

  if (!careers.length) {
    return (
      <>
        {header}
        <EmptyState title="No saved careers yet" action={{ href: '#/careers', label: 'Explore careers' }}>
          Save a career from its page or from Explore, and it will wait for you here.
        </EmptyState>
      </>
    )
  }

  return (
    <>
      {header}
      <ul className="career-grid">
        {careers.map((c) => (
          <li key={c.career_code} className="card career-card">
            <p className="mono">{capitalise(c.domain)}</p>
            <h2><a href={`#/careers/${c.career_code}`}>{c.title}</a></h2>
            <p className="result-summary clamp">{c.description}</p>
            <p className="career-meta">
              {c.match ? (
                <Pill tone="ok">Your match #{c.match.rank} · {c.match.score.toFixed(2)}</Pill>
              ) : (
                <Pill>Not linked to your skills</Pill>
              )}
            </p>
            <div className="card-foot">
              <span className="card-links">
                <a href={`#/careers/${c.career_code}`}>Details <Icon name="forward" size={14} /></a>
                {c.match && <a href={`#/roadmap/${c.career_code}`}>Roadmap <Icon name="forward" size={14} /></a>}
              </span>
              {/* Unsaving keeps the card until the next visit, so a slip is easy to undo. */}
              <SaveButton code={c.career_code} saved compact />
            </div>
          </li>
        ))}
      </ul>
    </>
  )
}
