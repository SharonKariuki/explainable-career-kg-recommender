import { useEffect, useState } from 'react'

import { getCareers } from '../api.js'
import { FilterChips, PageHeader, Pill, SaveButton, SearchField, Status } from '../components.jsx'
import { capitalise, domainOptions } from '../format.js'
import { Icon } from '../icons.jsx'

const SHOW = [
  { value: 'all', label: 'All careers' },
  { value: 'matched', label: 'Linked to my skills' },
  { value: 'saved', label: 'Saved' },
]

function filterCareers(careers, show, domain, query) {
  const q = query.trim().toLowerCase()
  return careers.filter(
    (c) =>
      (show === 'all' || (show === 'matched' ? c.match : c.saved)) &&
      (domain === 'all' || c.domain === domain) &&
      (!q || c.title.toLowerCase().includes(q) || c.description.toLowerCase().includes(q)),
  )
}

export default function CareersScreen() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [show, setShow] = useState('all')
  const [domain, setDomain] = useState('all')
  const [query, setQuery] = useState('')

  useEffect(() => {
    let current = true
    getCareers()
      .then((result) => current && setData(result))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  const header = (
    <PageHeader
      title="Explore careers"
      subtitle="Every tech career AjiraGuide knows, with your match where your skills link to it."
    />
  )

  if (!data) return <>{header}<Status loading={!error} error={error} /></>

  // A save made on a card is kept here too, so the Saved filter stays current.
  function savedChanged(code, saved) {
    setData({ ...data, careers: data.careers.map((c) => (c.career_code === code ? { ...c, saved } : c)) })
  }

  const careers = data.careers
  const showOptions = SHOW.map((o) => ({ ...o, count: filterCareers(careers, o.value, 'all', '').length }))
  const shown = filterCareers(careers, show, domain, query)

  return (
    <>
      {header}
      <div className="controls">
        <SearchField label="Search careers" value={query} onChange={setQuery} placeholder="Search careers" />
        <FilterChips label="Show" options={showOptions} value={show} onChange={setShow} />
        <FilterChips label="Filter by domain" options={domainOptions(careers)} value={domain} onChange={setDomain} />
      </div>

      {!data.skills.length && (
        <p className="muted small">
          <a href="#/assessment">Add your skills</a> to see how well you match each career.
        </p>
      )}

      {shown.length ? (
        <ul className="career-grid">
          {shown.map((c) => (
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
                <span className="muted small num">{c.skill_count} skills · {c.tool_count} tools</span>
              </p>
              <div className="card-foot">
                <a href={`#/careers/${c.career_code}`}>Details <Icon name="forward" size={14} /></a>
                <SaveButton
                  code={c.career_code}
                  saved={c.saved}
                  compact
                  onChange={(saved) => savedChanged(c.career_code, saved)}
                />
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
