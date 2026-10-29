import { useEffect, useState } from 'react'

import { getProfile, getProgress, getRecommendation, getRecommendations, saveProfile, setProgress } from '../api.js'
import { EmptyState, Notice, PageHeader, Pill, Progress, Segmented, Status } from '../components.jsx'
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

const STATUSES = [
  { value: 'todo', label: 'To do' },
  { value: 'learning', label: 'Learning' },
  { value: 'done', label: 'Done' },
]

function statusMap(progress) {
  return Object.fromEntries(progress.skills.map((p) => [p.skill_id, p.status]))
}

function RoadmapDetail({ code }) {
  const [career, setCareer] = useState(null)
  const [statuses, setStatuses] = useState({})
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null) // the skill being updated
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let current = true
    Promise.all([getRecommendation(code), getProgress()])
      .then(([result, progress]) => {
        if (!current) return
        setCareer(result)
        setStatuses(statusMap(progress))
      })
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [code, reload])

  async function changeStatus(skillId, status) {
    setBusy(skillId)
    setError(null)
    try {
      setStatuses(statusMap(await setProgress(skillId, status)))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  // A learned skill joins the profile, so the ranking and this roadmap count it.
  async function addToProfile(skillId, label) {
    setBusy(skillId)
    setError(null)
    try {
      const profile = await getProfile()
      await saveProfile([...profile.skills, label])
      setReload((n) => n + 1)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  if (!career) return <Status loading={!error} error={error} />

  const have = career.skill_contributions
  const gap = career.skills_gap
  const statusOf = (g) => statuses[g.skill_id] || 'todo'
  const done = gap.filter((g) => statusOf(g) === 'done').length
  const learning = gap.filter((g) => statusOf(g) === 'learning').length

  return (
    <>
      <section className="card panel roadmap-summary">
        <div className="grow">
          <p className="mono">Match #{career.rank} · {career.domain}</p>
          <h2>{career.title}</h2>
          <p className="muted small num">
            Uses {have.length} of your skills · {done} of {gap.length} to build done · {learning} learning
          </p>
          <Progress value={gap.length ? done / gap.length : 1} tone="gold" label={`${done} of ${gap.length} skills done`} />
        </div>
        <a className="btn glass" href={`#/careers/${code}`}>Details</a>
      </section>

      <Notice icon="bulb" title="How skills to build are ordered">
        Skills the career needs most come first; among those, skills distinctive to this career lead over ones nearly
        every career needs. Your progress is saved to your account.
      </Notice>

      {error && <Status error={error} />}

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
              {gap.map((g, i) => {
                const status = statusOf(g)
                return (
                  <li key={g.skill_id} className={`row roadmap-row ${status}`}>
                    <span className="av num" aria-label={`Priority ${i + 1}`}>
                      {status === 'done' ? <Icon name="check" size={16} /> : i + 1}
                    </span>
                    <span className="row-main">
                      <b>{g.label}</b>
                      <span className="sub">{capitalise(g.skill_type)} · {sourceNames(g.sources)} · {g.requirement}</span>
                      <span className="roadmap-controls">
                        <Segmented
                          label={`Progress on ${g.label}`}
                          options={STATUSES}
                          value={status}
                          onChange={(next) => changeStatus(g.skill_id, next)}
                          disabled={busy === g.skill_id}
                        />
                        {status === 'done' && (
                          <button
                            type="button"
                            className="link small"
                            onClick={() => addToProfile(g.skill_id, g.label)}
                            disabled={busy === g.skill_id}
                          >
                            Add to my skills
                          </button>
                        )}
                      </span>
                    </span>
                  </li>
                )
              })}
            </ol>
          ) : (
            <p className="empty">Your profile already covers every skill this career requires.</p>
          )}
        </section>
      </div>
    </>
  )
}
