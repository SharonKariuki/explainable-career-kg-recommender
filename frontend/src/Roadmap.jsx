// A career's skills plan drawn as a roadmap: stages down a central spine, each
// stage's skills branching off it. Choosing a skill opens its details and, for a
// skill still to build, its to do / learning / done control.

import { useEffect, useRef, useState } from 'react'

import { Pill, Segmented } from './components.jsx'
import { PLAN_STATUSES, capitalise, sourceNames } from './format.js'
import { Icon } from './icons.jsx'
import { WIDE, layoutRoadmap } from './roadmap.js'

const STATE_NAMES = { have: 'in your profile', todo: 'to do', learning: 'learning', done: 'done' }
const DETAIL_W = 300
const DETAIL_ROOM = 200 // space a skill's details need below it before they open above instead

function Legend() {
  return (
    <ul className="rm-legend" aria-label="Key">
      <li><span className="rm-key have"><Icon name="check" size={10} /></span>In your profile</li>
      <li><span className="rm-key learning" />Learning</li>
      <li><span className="rm-key done"><Icon name="check" size={10} /></span>Done</li>
      <li><span className="rm-key line" />Follow the line down: most needed first</li>
    </ul>
  )
}

function Detail({ box, layout, busy, onStatus, onAdd, onClose }) {
  const ref = useRef(null)
  const { node } = box
  const { skill, state } = node
  useEffect(() => ref.current?.focus(), [])

  const style = layout.compact
    ? { left: 0, width: layout.width }
    : { width: DETAIL_W, left: box.side === 'left' ? box.x : box.x + box.w - DETAIL_W }
  if (layout.height - (box.y + box.h) < DETAIL_ROOM && box.y > DETAIL_ROOM) style.bottom = layout.height - box.y + 8
  else style.top = box.y + box.h + 8

  const meta = [capitalise(skill.skill_type || 'skill'), skill.sources && sourceNames(skill.sources)].filter(Boolean).join(' · ')

  return (
    <div ref={ref} className="rm-detail card" style={style} role="dialog" aria-label={node.label} tabIndex={-1}>
      <div className="rm-detail-head">
        <b>{node.label}</b>
        <button type="button" className="rm-close" onClick={onClose} aria-label="Close"><Icon name="close" size={16} /></button>
      </div>
      {state === 'have' ? (
        <>
          <p className="muted small">In your profile. You said “{skill.query}”.</p>
          <p className="rm-pills">
            <Pill>{skill.requirement}</Pill>
            {skill.low_confidence && <Pill tone="warn">Uncertain</Pill>}
          </p>
        </>
      ) : (
        <>
          <p className="muted small">{meta}</p>
          <p className="rm-pills"><Pill>{skill.requirement}</Pill></p>
          <div className="roadmap-controls">
            <Segmented label={`Progress on ${node.label}`} options={PLAN_STATUSES} value={state} onChange={(next) => onStatus(node.id, next)} disabled={busy} />
            {state === 'done' && (
              <button type="button" className="link small" onClick={() => onAdd(node.id, node.label)} disabled={busy}>Add to my skills</button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

// sections: from roadmapSections. busy: the id of the skill being saved.
// onStatus(skillId, status) and onAdd(skillId, label) are async.
export default function Roadmap({ title, sections, busy, onStatus, onAdd }) {
  const frame = useRef(null)
  const [available, setAvailable] = useState(WIDE)
  const [open, setOpen] = useState(null)

  useEffect(() => {
    const el = frame.current
    if (!el || typeof ResizeObserver === 'undefined') return undefined
    const observer = new ResizeObserver(([entry]) => setAvailable(Math.floor(entry.contentRect.width)))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const layout = layoutRoadmap(sections, available)
  const opened = layout.boxes.find((b) => b.kind === 'skill' && b.key === open)
  const toBuild = sections.some((s) => s.key !== 'have')

  function close() {
    const id = open
    setOpen(null)
    frame.current?.querySelector(`[data-skill="${CSS.escape(id)}"]`)?.focus()
  }

  return (
    <div ref={frame} className="rm-frame">
      <Legend />
      <div
        className={`rm-canvas${layout.compact ? ' compact' : ''}`}
        style={{ width: layout.width, height: layout.height }}
        onKeyDown={(e) => e.key === 'Escape' && open && close()}
      >
        <svg className="rm-lines" width={layout.width} height={layout.height} aria-hidden="true">
          <path className="rm-spine" d={layout.spine} />
          {layout.branches.map((d) => <path key={d} className="rm-branch" d={d} />)}
        </svg>
        {layout.boxes.map((b) => {
          const style = { left: b.x, top: b.y, width: b.w, height: b.h }
          if (b.kind === 'title') return <div key={b.key} className="rm-box rm-title" style={style}><span>{title}</span></div>
          if (b.kind === 'end') {
            return <div key={b.key} className="rm-box rm-end" style={style}><span>{toBuild ? 'Ready for this career' : 'You cover every required skill'}</span></div>
          }
          if (b.kind === 'topic') {
            return (
              <div key={b.key} className="rm-box rm-topic" style={style}>
                <span>{b.section.label}</span>
                <span className="rm-count num" aria-label={`${b.section.done} of ${b.section.skills.length} done`}>{b.section.done}/{b.section.skills.length}</span>
              </div>
            )
          }
          const { node } = b
          return (
            <button
              key={b.key}
              type="button"
              data-skill={node.id}
              className={`rm-box rm-skill ${node.state}${open === node.id ? ' open' : ''}`}
              style={style}
              title={node.label}
              aria-expanded={open === node.id}
              aria-label={`${node.label}, ${STATE_NAMES[node.state]}`}
              onClick={() => setOpen(open === node.id ? null : node.id)}
            >
              <span>{node.label}</span>
              {node.state !== 'todo' && (
                <i className="rm-badge" aria-hidden="true">{node.state !== 'learning' && <Icon name="check" size={11} />}</i>
              )}
            </button>
          )
        })}
        {opened && (
          <Detail key={opened.key} box={opened} layout={layout} busy={busy === opened.key} onStatus={onStatus} onAdd={onAdd} onClose={close} />
        )}
      </div>
    </div>
  )
}
