import { useEffect, useState } from 'react'

import { getRecommendations } from '../api.js'
import { Disclosure, EmptyState, FilterChips, IconButton, MatchBadge, Notice, PageHeader, Pill, SearchField, SkillChip, Status } from '../components.jsx'
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

  const shown = filterRecommendations(data.recommendations, domain, query)

  return (
    <>
      {header}

      <SkillReading matches={data.matches} />

      <div className="controls">
        <SearchField label="Search your matches" value={query} onChange={setQuery} placeholder="Search career or skill" />
        <FilterChips label="Filter by domain" options={domainOptions(data.recommendations)} value={domain} onChange={setDomain} />
      </div>

      {shown.length ? (
        <ol className="results">
          {shown.map((r) => <MatchCard key={r.career_code} match={r} />)}
        </ol>
      ) : (
        <p className="empty">No matches fit this search.</p>
      )}
    </>
  )
}

// How each typed skill was read. Uncertain matches are named outside the
// collapsed list, so they are never hidden.
export function SkillReading({ matches }) {
  const uncertain = matches.filter((m) => m.low_confidence)
  return (
    <>
      {uncertain.length > 0 && (
        <Notice icon="alert" title="Some skills had no close match" action={{ href: '#/assessment', label: 'Reword' }}>
          {uncertain.map((m) => `“${m.query}” was read as ${m.skill}`).join('; ')}. They count for less in your ranking.
        </Notice>
      )}
      <section className="card panel">
        <Disclosure summary={`How we read your ${matches.length} skills`}>
          <ul className="matches">
            {matches.map((m) => (
              <li key={m.query}>
                <span className="match-query">{m.query}</span>
                {m.query.toLowerCase() !== m.skill.toLowerCase() && (
                  <span className="muted"><Icon name="forward" size={12} /> {m.skill}</span>
                )}
                {m.low_confidence && <Pill tone="warn">Unsure match</Pill>}
              </li>
            ))}
          </ul>
          <p className="muted small"><a href="#/assessment">Edit your skills</a></p>
        </Disclosure>
      </section>
    </>
  )
}

export function MatchCard({ match: r }) {
  return (
    <li className="card result">
      <div className="result-head">
        <span className="av num"><span className="visually-hidden">Rank </span>{r.rank}</span>
        <div className="grow">
          <h2><a href={`#/careers/${r.career_code}`}>{r.title}</a></h2>
          <p className="sub">{capitalise(r.domain)}</p>
        </div>
        <MatchBadge fit={r.fit} score={r.score} />
      </div>
      <p className="result-summary">{r.reason}</p>
      {r.matched_skills.length > 0 && (
        <ul className="chips skill-chips" aria-label="Your skills this career uses">
          {r.matched_skills.map((s) => <SkillChip key={s.skill_id} skill={s} />)}
        </ul>
      )}
      <div className="card-links">
        <a href={`#/careers/${r.career_code}`}>See why it fits<span className="visually-hidden">: {r.title}</span> <Icon name="forward" size={14} /></a>
        <a href={`#/roadmap/${r.career_code}`}>Skills roadmap<span className="visually-hidden"> for {r.title}</span> <Icon name="forward" size={14} /></a>
      </div>
    </li>
  )
}
