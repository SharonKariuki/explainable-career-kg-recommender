// A small view of the knowledge graph around one career: the user's skills
// that it requires (left), the career (centre) and the top skills to build
// (right). Edge thickness follows how strongly the career needs each skill.

const WIDTH = 760
const ROW = 46
const NODE_W = 226
const NODE_H = 32
const CAREER_W = 204
const CAREER_H = 52
const COLUMNS = { left: 10, centre: (WIDTH - CAREER_W) / 2, right: WIDTH - NODE_W - 10 }
const MAX_CHARS = 31

function short(text) {
  return text.length > MAX_CHARS ? `${text.slice(0, MAX_CHARS - 1)}…` : text
}

function column(items, height) {
  const top = (height - items.length * ROW) / 2
  return items.map((item, i) => ({ ...item, y: top + i * ROW + (ROW - NODE_H) / 2 }))
}

// Split a long title over two lines at the space nearest its middle.
function twoLines(text) {
  if (text.length <= 22) return [text]
  const spaces = [...text.matchAll(/ /g)].map((m) => m.index)
  const cut = spaces.reduce((best, i) => (Math.abs(i - text.length / 2) < Math.abs(best - text.length / 2) ? i : best), spaces[0])
  return cut === undefined ? [short(text)] : [short(text.slice(0, cut)), short(text.slice(cut + 1))]
}

function Node({ x, y, label, className, width = NODE_W, height = NODE_H, wrap = false }) {
  const lines = wrap ? twoLines(label) : [short(label)]
  return (
    <g className={className}>
      <title>{label}</title>
      <rect x={x} y={y} width={width} height={height} rx="8" />
      <text x={x + width / 2} y={y + height / 2} dominantBaseline="central" textAnchor="middle">
        {lines.map((line, i) => (
          <tspan key={line} x={x + width / 2} dy={i === 0 ? `${-(lines.length - 1) * 0.6}em` : '1.2em'}>{line}</tspan>
        ))}
      </text>
    </g>
  )
}

export default function CareerGraph({ career, gapLimit = 5 }) {
  const have = career.skill_contributions.map((s) => ({
    key: s.skill_id, label: s.skill_label, weight: s.edge_weight, uncertain: s.low_confidence,
  }))
  const build = career.skills_gap.slice(0, gapLimit).map((g) => ({ key: g.skill_id, label: g.label, weight: g.edge_weight }))
  const height = Math.max(have.length, build.length, 2) * ROW + 20
  const left = column(have, height)
  const right = column(build, height)
  const centreY = (height - CAREER_H) / 2
  const midY = centreY + CAREER_H / 2
  const stroke = (weight) => 1.5 + weight * 4

  const description =
    `${career.title} uses ${have.length ? have.map((s) => s.label).join(', ') : 'none of your listed skills'}; ` +
    `skills to build: ${build.map((s) => s.label).join(', ')}.`

  return (
    <figure className="career-graph">
      {/* Phones: the same connections, stacked so they stay readable. */}
      <div className="graph-narrow">
        <ul className="chips">
          {have.map((s) => <li key={s.key} className={s.uncertain ? 'chip uncertain' : 'chip'}>{s.label}</li>)}
          {!have.length && <li className="muted">none of your skills directly</li>}
        </ul>
        <div className="graph-arrow" aria-hidden="true">↓</div>
        <div className="graph-career">{career.title}</div>
        <div className="graph-arrow" aria-hidden="true">↓ <span className="muted">skills to build</span></div>
        <ul className="chips">
          {build.map((s) => <li key={s.key} className="chip build">{s.label}</li>)}
        </ul>
      </div>
      <div className="career-graph-scroll">
        <svg viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-label={description}>
          {left.map((s) => (
            <path
              key={`e-${s.key}`}
              className={s.uncertain ? 'edge uncertain' : 'edge have'}
              d={`M ${COLUMNS.left + NODE_W} ${s.y + NODE_H / 2} C ${COLUMNS.centre - 40} ${s.y + NODE_H / 2}, ${COLUMNS.left + NODE_W + 40} ${midY}, ${COLUMNS.centre} ${midY}`}
              strokeWidth={stroke(s.weight)}
            />
          ))}
          {right.map((s) => (
            <path
              key={`e-${s.key}`}
              className="edge build"
              d={`M ${COLUMNS.centre + CAREER_W} ${midY} C ${COLUMNS.right - 40} ${midY}, ${COLUMNS.centre + CAREER_W + 40} ${s.y + NODE_H / 2}, ${COLUMNS.right} ${s.y + NODE_H / 2}`}
              strokeWidth={stroke(s.weight)}
            />
          ))}
          {left.map((s) => (
            <Node key={s.key} x={COLUMNS.left} y={s.y} label={s.label} className={s.uncertain ? 'node uncertain' : 'node have'} />
          ))}
          {!left.length && (
            <text className="graph-note" x={COLUMNS.left + NODE_W / 2} y={midY} textAnchor="middle" dominantBaseline="central">
              none of your skills directly
            </text>
          )}
          <Node x={COLUMNS.centre} y={centreY} label={career.title} className="node career" width={CAREER_W} height={CAREER_H} wrap />
          {right.map((s) => (
            <Node key={s.key} x={COLUMNS.right} y={s.y} label={s.label} className="node build" />
          ))}
        </svg>
      </div>
      <figcaption className="muted">
        Your skills this career requires, and the top skills to build.
        <span className="wide-only"> Thicker lines mean the career needs the skill more.</span>
        {have.some((s) => s.uncertain) && ' Dashed amber marks an uncertain match.'}
      </figcaption>
    </figure>
  )
}
