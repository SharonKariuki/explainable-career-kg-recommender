import { useEffect, useState } from 'react'

import { getRecommendations } from '../api.js'
import { EmptyState, FilterChips, PageHeader, SearchField, Status } from '../components.jsx'
import { domainOptions, filterRecommendations } from '../format.js'
import { Icon } from '../icons.jsx'

// The API caps top at 50, above the number of careers, so this lists every
// career the engine ranks: those requiring at least one of the user's skills.
const ALL_CAREERS = 50

export default function CareersScreen() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [domain, setDomain] = useState('all')
  const [query, setQuery] = useState('')

  useEffect(() => {
    let current = true
    getRecommendations(ALL_CAREERS)
      .then((result) => current && setData(result))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  const subtitle = data?.recommendations.length
    ? `${data.recommendations.length} careers require at least one of your skills, best fit first.`
    : 'Careers that require at least one of your skills.'
  const header = <PageHeader title="Explore careers" subtitle={subtitle} />

  if (!data) return <>{header}<Status loading={!error} error={error} /></>

  if (!data.recommendations.length) {
    return (
      <>
        {header}
        <EmptyState
          title={data.skills.length ? 'No careers linked yet' : 'Add skills to explore careers'}
          action={{ href: '#/assessment', label: data.skills.length ? 'Reword your skills' : 'Add your skills' }}
        >
          Careers appear here once one of your skills matches a skill they require.
        </EmptyState>
      </>
    )
  }

  const shown = filterRecommendations(data.recommendations, domain, query)

  return (
    <>
      {header}
      <div className="controls">
        <SearchField label="Search careers" value={query} onChange={setQuery} placeholder="Search career or skill" />
        <FilterChips label="Filter by domain" options={domainOptions(data.recommendations)} value={domain} onChange={setDomain} />
      </div>

      {shown.length ? (
        <ul className="career-grid">
          {shown.map((r) => (
            <li key={r.career_code} className="card career-card">
              <p className="mono">#{r.rank} · {r.domain}</p>
              <h2><a href={`#/careers/${r.career_code}`}>{r.title}</a></h2>
              <p className="result-summary">{r.summary}</p>
              <div className="card-links">
                <a href={`#/careers/${r.career_code}`}>Details <Icon name="forward" size={14} /></a>
                <a href={`#/roadmap/${r.career_code}`}>Roadmap <Icon name="forward" size={14} /></a>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">No careers fit this search.</p>
      )}
    </>
  )
}
