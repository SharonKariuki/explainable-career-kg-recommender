// The skills plan drawn as a roadmap: a spine of stages running down the page,
// with each stage's skills branching off it. This file groups the skills into
// stages and works out where every box and line goes; Roadmap.jsx draws them.

const TIERS = [
  { key: 'core', requirement: 'Core requirement', label: 'Core requirements' },
  { key: 'important', requirement: 'Important', label: 'Important skills' },
  { key: 'supporting', requirement: 'Supporting', label: 'Supporting skills' },
]

// have: the student's skills the career uses; gap: skills to build, most important first;
// statuses: { skill id: 'learning' | 'done' }. Returns the stages that have skills, in order:
// [{ key, label, done, skills: [{ id, label, side, state, skill }] }].
// Tools branch right and everything else left; state is 'have', 'todo', 'learning' or 'done'.
export function roadmapSections(have, gap, statuses = {}) {
  const sections = []
  if (have.length) {
    sections.push({
      key: 'have',
      label: 'You already have',
      skills: have.map((s, i) => ({ id: s.skill_id, label: s.skill_label, side: i % 2 ? 'right' : 'left', state: 'have', skill: s })),
    })
  }
  const known = new Set(TIERS.map((t) => t.requirement))
  for (const tier of TIERS) {
    const last = tier === TIERS[TIERS.length - 1]
    // A requirement label this file does not know is still shown, in the last stage.
    const skills = gap
      .filter((g) => g.requirement === tier.requirement || (last && !known.has(g.requirement)))
      .map((g) => ({ id: g.skill_id, label: g.label, side: g.skill_type === 'tool' ? 'right' : 'left', state: statuses[g.skill_id] || 'todo', skill: g }))
    if (skills.length) sections.push({ key: tier.key, label: tier.label, skills })
  }
  return sections.map((s) => ({ ...s, done: s.skills.filter((k) => k.state === 'have' || k.state === 'done').length }))
}

export const WIDE = 860
const COMPACT_BELOW = 640
const TITLE_H = 52
const TOPIC_H = 48
const SKILL_H = 44
const END_H = 44

// Boxes and lines for the sections at a given canvas width. Below COMPACT_BELOW the
// skills stack under their stage instead of branching to both sides.
// Returns { width, height, compact, boxes: [{ kind, key, x, y, w, h, ... }], spine, branches }
// where spine and each branch are SVG path strings.
export function layoutRoadmap(sections, available = WIDE) {
  const compact = available < COMPACT_BELOW
  return compact ? stacked(sections, Math.max(available, 240)) : branching(sections, Math.min(Math.max(available, 680), 900))
}

function branching(sections, width) {
  const pitch = SKILL_H + 12
  const gap = 44
  const topicW = 220
  const skillW = Math.min(230, (width - topicW) / 2 - 70)
  const cx = width / 2
  const boxes = [{ kind: 'title', key: 'title', x: cx - 140, y: 0, w: 280, h: TITLE_H }]
  const branches = []
  let y = TITLE_H + gap

  for (const section of sections) {
    const sides = { left: section.skills.filter((s) => s.side === 'left'), right: section.skills.filter((s) => s.side === 'right') }
    const rows = Math.max(sides.left.length, sides.right.length, 1)
    const blockH = rows * pitch - (pitch - SKILL_H)
    const topicY = y + (blockH - TOPIC_H) / 2
    const midY = topicY + TOPIC_H / 2
    boxes.push({ kind: 'topic', key: section.key, section, x: cx - topicW / 2, y: topicY, w: topicW, h: TOPIC_H })

    for (const side of ['left', 'right']) {
      const items = sides[side]
      const top = y + ((rows - items.length) * pitch) / 2 // the shorter side is centred on the stage
      const x = side === 'left' ? 0 : width - skillW
      const from = side === 'left' ? cx - topicW / 2 : cx + topicW / 2
      const to = side === 'left' ? skillW : width - skillW
      const bend = (from + to) / 2
      items.forEach((node, i) => {
        const nodeY = top + i * pitch
        const nodeMid = nodeY + SKILL_H / 2
        boxes.push({ kind: 'skill', key: node.id, node, side, x, y: nodeY, w: skillW, h: SKILL_H })
        branches.push(`M ${from} ${midY} C ${bend} ${midY}, ${bend} ${nodeMid}, ${to} ${nodeMid}`)
      })
    }
    y += blockH + gap
  }

  boxes.push({ kind: 'end', key: 'end', x: cx - topicW / 2, y, w: topicW, h: END_H })
  return { width, height: y + END_H, compact: false, boxes, spine: `M ${cx} ${TITLE_H} V ${y}`, branches }
}

function stacked(sections, width) {
  const rail = 14 // the spine runs down the left edge, beside the indented skills
  const indent = 32
  const boxes = [{ kind: 'title', key: 'title', x: 0, y: 0, w: width, h: TITLE_H }]
  const branches = []
  let y = TITLE_H + 22

  for (const section of sections) {
    boxes.push({ kind: 'topic', key: section.key, section, x: 0, y, w: width, h: TOPIC_H })
    y += TOPIC_H + 10
    for (const node of section.skills) {
      boxes.push({ kind: 'skill', key: node.id, node, side: 'right', x: indent, y, w: width - indent, h: SKILL_H })
      branches.push(`M ${rail} ${y + SKILL_H / 2} H ${indent}`)
      y += SKILL_H + 10
    }
    y += 12
  }

  boxes.push({ kind: 'end', key: 'end', x: 0, y, w: width, h: END_H })
  return { width, height: y + END_H, compact: true, boxes, spine: `M ${rail} ${TITLE_H} V ${y}`, branches }
}
