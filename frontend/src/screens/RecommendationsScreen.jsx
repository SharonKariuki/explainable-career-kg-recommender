import { useEffect, useState } from 'react'

import { getRecommendations } from '../api.js'
import { EmptyState, FilterChips, IconButton, Meter, Notice, PageHeader, Pill, SearchField, Status } from '../components.jsx'
import { capitalise, domainOptions, filterRecommendations } from '../format.js'
import { Icon } from '../icons.jsx'

export default function RecommendationsScreen() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [domain, setDomain] = useState('all')
  const [query, setQuery] = useState('')

  useEffect(() => {
    let current = true
    getRecommendations(10)
      .then((result) => current && setData(result))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  const header = (
    <PageHeader title="Your career matches" subtitle="Your top 10, ranked by how well your skills fit.">
      <IconButton icon="edit" label="Edit your skills" href="#/assessment" />
    </PageHeader>
  )

  if (!data) return <>{header}<Status loading={!error} error={error} /></>

  if (!data.skills.length) {
    return (
      <>
        {header}
        <EmptyState title="You have not listed any skills yet" action={{ href: '#/assessment', label: 'Add your skills' }} />
      </>
    )
  }

  const uncertain = data.matches.filter((m) => m.low_confidence)
  const shown = filterRecommendations(data.recommendations, domain, query)

  return (
    <>
      {header}

      <section className="card panel">
        <div className="ph">
          <h2>How we read your skills</h2>
          <a href="#/assessment">Edit</a>
        </div>
        <ul className="matches">
          {data.matches.map((m) => (
            <li key={m.query}>
              <span className="match-query">{m.query}</span>
              {m.query.toLowerCase() !== m.skill.toLowerCase() && (
                <span className="muted"><Icon name="forward" size={12} /> {m.skill}</span>
              )}
              {m.low_confidence && <Pill tone="warn">Uncertain</Pill>}
            </li>
          ))}
        </ul>
      </section>

      {uncertain.length > 0 && (
        <Notice icon="alert" title="Some skills had no close match" action={{ href: '#/assessment', label: 'Reword' }}>
          They count for less in your ranking. Rewording them may help.
        </Notice>
      )}

      <div className="controls">
        <SearchField label="Search your matches" value={query} onChange={setQuery} placeholder="Search career or skill" />
        <FilterChips label="Filter by domain" options={domainOptions(data.recommendations)} value={domain} onChange={setDomain} />
      </div>

      {shown.length ? (
        <ol className="results">
          {shown.map((r) => (
            <li key={r.career_code} className="card result">
              <div className="result-head">
                <span className="av num">{r.rank}</span>
                <div className="grow">
                  <h2><a href={`#/careers/${r.career_code}`}>{r.title}</a></h2>
                  <p className="sub">{capitalise(r.domain)}</p>
                </div>
                <div className="score" title="Overall score, 0 to 1">
                  <strong className="num">{r.score.toFixed(2)}</strong>
                  <span className="sub">score</span>
                </div>
              </div>
              <p className="result-summary">{r.summary}</p>
              <div className="meters">
                <Meter label="Coverage" value={r.components.coverage} />
                <Meter label="Similarity" value={r.components.profile_similarity} />
                <Meter label="Proximity" value={r.components.graph_proximity} />
              </div>
              <div className="card-links">
                <a href={`#/careers/${r.career_code}`}>Why this career <Icon name="forward" size={14} /></a>
                <a href={`#/roadmap/${r.career_code}`}>Skills roadmap <Icon name="forward" size={14} /></a>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="empty">No matches fit this search.</p>
      )}
    </>
  )
}
