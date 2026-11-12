import { useEffect, useState } from 'react'

import { getHistory, getHistoryRun } from '../api.js'
import { Disclosure, EmptyState, PageHeader, Pill, Status } from '../components.jsx'
import { capitalise, movement, when } from '../format.js'
import { Icon } from '../icons.jsx'

const BACK = { href: '#/history', label: 'All snapshots' }

function RunList({ runs }) {
  return (
    <ul className="list card history-list">
      {runs.map((run) => (
        <li key={run.id}>
          <a href={`#/history/${run.id}`} className="history-row">
            <span className="grow">
              <strong>{when(run.created_at)}</strong>
              <span className="muted small block">
                {run.skills.length} skills{run.has_background ? ' and your background' : ''}:{' '}
                {run.top.map((t) => t.title).join(', ')}
              </span>
            </span>
            {run.changed && <Pill tone="ok">Top 3 changed</Pill>}
            <Icon name="forward" size={16} />
          </a>
        </li>
      ))}
    </ul>
  )
}

export function RunDetail({ run }) {
  return (
    <>
      <section className="card panel">
        <p className="mono">Skills</p>
        <ul className="chips" aria-label="Skills in this snapshot">
          {run.skills.map((s) => <li key={s} className="chip">{s}</li>)}
        </ul>
        {run.background && <p className="muted small">Background: {run.background}</p>}
      </section>
      <ol className="list card history-detail">
        {run.recommendations.map((r) => {
          const move = run.previous_id ? movement(r.rank, r.previous_rank) : null
          return (
            <li key={r.career_code}>
              <div className="history-row">
                <span className="num rank">#{r.rank}</span>
                <span className="grow">
                  <a href={`#/careers/${r.career_code}`}><strong>{r.title}</strong></a>
                  <span className="muted small block">{capitalise(r.domain)} · {capitalise(r.fit)} match · score {r.score.toFixed(2)}</span>
                </span>
                {move && <Pill tone={move.tone}>{move.label}</Pill>}
              </div>
              <Disclosure summary="Why, and skills to build">
                {r.explanation.map((sentence) => <p key={sentence}>{sentence}</p>)}
                {r.skill_gaps.length > 0 && (
                  <p className="muted small">Skills to build: {r.skill_gaps.map((g) => g.label).join(', ')}</p>
                )}
              </Disclosure>
            </li>
          )
        })}
      </ol>
    </>
  )
}

export default function HistoryScreen({ runId }) {
  const [runs, setRuns] = useState(null)
  const [run, setRun] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let current = true
    const load = runId ? getHistoryRun(runId).then((r) => current && setRun(r)) : getHistory().then((r) => current && setRuns(r.runs))
    load.catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [runId])

  if (runId) {
    const header = <PageHeader title={run ? `Matches on ${when(run.created_at)}` : 'Snapshot'} back={BACK}
      subtitle="What AjiraGuide recommended then, and how each career moved since the snapshot before." />
    if (!run) return <>{header}<Status loading={!error} error={error} /></>
    return <>{header}<RunDetail run={run} /></>
  }

  const header = <PageHeader title="History" subtitle="A snapshot of your matches each time you change your skills or background, newest first." />
  if (!runs) return <>{header}<Status loading={!error} error={error} /></>
  if (!runs.length) {
    return (
      <>
        {header}
        <EmptyState title="No history yet" action={{ href: '#/assessment', label: 'Add your skills' }}>
          Save your skills and your matches will be recorded here, so you can see how they change as you grow.
        </EmptyState>
      </>
    )
  }
  return <>{header}<RunList runs={runs} /></>
}
