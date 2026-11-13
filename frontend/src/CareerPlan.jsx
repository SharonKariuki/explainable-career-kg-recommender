// A career's skills plan: what the student already brings, and each skill still
// to build with its to do / learning / done control. Works for any career; one
// outside the student's matches lists what the career requires instead of a gap.

import { useEffect, useState } from 'react'

import { getProfile, getProgress, saveProfile, setProgress } from './api.js'
import { Notice, Pill, Progress, Segmented, Status } from './components.jsx'
import { PLAN_STATUSES, capitalise, sourceNames, statusMap } from './format.js'
import { Icon } from './icons.jsx'
import Roadmap from './Roadmap.jsx'
import { roadmapSections } from './roadmap.js'

const VIEWS = [
  { value: 'roadmap', label: 'Roadmap' },
  { value: 'list', label: 'List' },
]

// One skill with its status control. onStatus(next) and onAdd() are async.
export function PlanRow({ skill, position, status, busy, onStatus, onAdd }) {
  const detail = [capitalise(skill.skill_type || 'skill'), skill.sources && sourceNames(skill.sources), skill.requirement]
  return (
    <li className={`row roadmap-row ${status}`}>
      <span className="av num" aria-label={position ? `Priority ${position}` : undefined}>
        {status === 'done' ? <Icon name="check" size={16} /> : position ?? <Icon name="roadmap" size={16} />}
      </span>
      <span className="row-main">
        <b>{skill.label}</b>
        <span className="sub">{detail.filter(Boolean).join(' · ')}</span>
        <span className="roadmap-controls">
          <Segmented label={`Progress on ${skill.label}`} options={PLAN_STATUSES} value={status} onChange={onStatus} disabled={busy} />
          {status === 'done' && onAdd && (
            <button type="button" className="link small" onClick={onAdd} disabled={busy}>Add to my skills</button>
          )}
        </span>
      </span>
    </li>
  )
}

// title: the career's name; have: the student's skills this career uses; gap: the skills to build, most important first.
// onProfileChanged runs after a finished skill joins the profile, so the page can reload.
export default function CareerPlan({ title, have, gap, matched, onProfileChanged }) {
  const [statuses, setStatuses] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null) // the skill being updated
  const [view, setView] = useState('roadmap')

  useEffect(() => {
    let current = true
    getProgress()
      .then((progress) => current && setStatuses(statusMap(progress.skills)))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  async function run(skillId, action) {
    setBusy(skillId)
    setError(null)
    try {
      await action()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  const changeStatus = (skillId, status) =>
    run(skillId, async () => setStatuses(statusMap((await setProgress(skillId, status)).skills)))

  // A learned skill joins the profile, so the ranking and this plan count it.
  const addToProfile = (skillId, label) =>
    run(skillId, async () => {
      const profile = await getProfile()
      await saveProfile([...profile.skills, label])
      onProfileChanged()
    })

  if (!statuses) return <Status loading={!error} error={error} />

  const statusOf = (g) => statuses[g.skill_id] || 'todo'
  const done = gap.filter((g) => statusOf(g) === 'done').length
  const learning = gap.filter((g) => statusOf(g) === 'learning').length

  return (
    <>
      <section className="card panel roadmap-summary">
        <div className="grow">
          <p className="mono">Your progress</p>
          <p className="muted small num">
            {matched ? `Uses ${have.length} of your skills · ` : ''}{done} of {gap.length} to build done · {learning} learning
          </p>
          <Progress value={gap.length ? done / gap.length : 1} tone="amber" label={`${done} of ${gap.length} skills done`} />
        </div>
        <a className="btn glass" href="#/plan">My plan</a>
      </section>

      {matched ? (
        <Notice icon="bulb" title="How skills to build are ordered">
          Skills the career needs most come first; among those, skills distinctive to this career lead over ones nearly
          every career needs. Your progress is saved to your account.
        </Notice>
      ) : (
        <Notice icon="bulb" title="None of your skills link to this career yet">
          These are the skills it requires most. Track the ones you start learning; a finished skill can join your
          profile, and the career is then ranked and explained for you.
        </Notice>
      )}

      {error && <Status error={error} />}

      <div className="plan-view">
        <Segmented label="Show the plan as" options={VIEWS} value={view} onChange={setView} />
      </div>

      {view === 'roadmap' ? (
        <section className="card panel rm-card" aria-label="Skills roadmap">
          <Roadmap title={title} sections={roadmapSections(have, gap, statuses)} busy={busy} onStatus={changeStatus} onAdd={addToProfile} />
        </section>
      ) : (
      <div className={matched ? 'split-2' : undefined}>
        {matched && (
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
        )}

        <section className="card panel">
          <div className="ph">
            <h2>{matched ? 'Skills to develop' : 'Skills this career requires'}</h2>
            <span>Highest priority first</span>
          </div>
          {gap.length ? (
            <ol className="list">
              {gap.map((g, i) => (
                <PlanRow
                  key={g.skill_id}
                  skill={g}
                  position={i + 1}
                  status={statusOf(g)}
                  busy={busy === g.skill_id}
                  onStatus={(next) => changeStatus(g.skill_id, next)}
                  onAdd={() => addToProfile(g.skill_id, g.label)}
                />
              ))}
            </ol>
          ) : (
            <p className="empty">Your profile already covers every skill this career requires.</p>
          )}
        </section>
      </div>
      )}
    </>
  )
}
