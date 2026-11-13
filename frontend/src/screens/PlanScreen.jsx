import { useEffect, useState } from 'react'

import { getProgress, getRecommendations, getSaved, setProgress } from '../api.js'
import { PlanRow } from '../CareerPlan.jsx'
import { EmptyState, PageHeader, Pill, Progress, Status } from '../components.jsx'
import { capitalise, planCareers, planCounts } from '../format.js'
import { Icon } from '../icons.jsx'

// Enough matches to suggest careers to plan for when few are saved.
const SUGGESTED = 3

// Every skill the student is learning or has finished, whichever career it came from.
export function SkillsInProgress({ progress, busy, onStatus }) {
  const { learning, done } = planCounts(progress)
  return (
    <section className="card panel" aria-labelledby="building-heading">
      <div className="ph">
        <h2 id="building-heading">Skills you are building</h2>
        <span className="num">{learning} learning · {done} done</span>
      </div>
      <Progress value={progress.length ? done / progress.length : 0} tone="amber" label={`${done} of ${progress.length} skills in your plan done`} />
      <ul className="list">
        {progress.map((p) => (
          <PlanRow key={p.skill_id} skill={p} status={p.status} busy={busy === p.skill_id} onStatus={(next) => onStatus(p.skill_id, next)} />
        ))}
      </ul>
      <p className="muted small">Setting a skill back to “To do” takes it off this list; it stays on its career's plan.</p>
    </section>
  )
}

// careers: [{ career_code, title, domain, rank, saved }] from planCareers.
export function CareersToPlan({ careers }) {
  return (
    <section className="card panel" aria-labelledby="careers-heading">
      <div className="ph">
        <h2 id="careers-heading">Careers to plan for</h2>
        <a href="#/careers">All careers</a>
      </div>
      <p className="muted small">Your saved careers and top matches. Open one to see its skills in order and track them.</p>
      <ul className="list">
        {careers.map((c) => (
          <li key={c.career_code}>
            <a className="row" href={`#/careers/${c.career_code}/plan`}>
              <span className="av"><Icon name={c.saved ? 'bookmark' : 'roadmap'} size={16} /></span>
              <span className="row-main">
                <b>{c.title}</b>
                <span className="sub">{capitalise(c.domain)}</span>
              </span>
              <span className="row-value">
                {c.saved && <Pill>Saved</Pill>}
                {c.rank ? <Pill tone="match">Match #{c.rank}</Pill> : <Pill>Not a match yet</Pill>}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function PlanScreen() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null)

  useEffect(() => {
    let current = true
    Promise.all([getProgress(), getSaved(), getRecommendations(SUGGESTED)])
      .then(([progress, saved, ranked]) => {
        if (current) setData({ progress: progress.skills, careers: planCareers(saved.careers, ranked.recommendations) })
      })
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  async function changeStatus(skillId, status) {
    setBusy(skillId)
    setError(null)
    try {
      const progress = await setProgress(skillId, status)
      setData((d) => ({ ...d, progress: progress.skills }))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  const header = <PageHeader title="My plan" subtitle="Everything you are learning, across every career you are working towards." />

  if (!data) return <>{header}<Status loading={!error} error={error} /></>

  return (
    <>
      {header}
      {error && <Status error={error} />}
      {data.progress.length ? (
        <SkillsInProgress progress={data.progress} busy={busy} onStatus={changeStatus} />
      ) : (
        <EmptyState title="Nothing in your plan yet" action={data.careers.length ? undefined : { href: '#/profile', label: 'Add your skills' }}>
          Open a career below, go to its Skills plan and mark the skills you start learning. They will gather here.
        </EmptyState>
      )}
      {data.careers.length > 0 && <CareersToPlan careers={data.careers} />}
    </>
  )
}
