// Formatting helpers shared by the recommendation screens.

const SOURCES = { onet_skill: 'O*NET rating', onet_tool: 'O*NET tools', esco: 'ESCO' }

export function sourceNames(sources) {
  return sources.map((s) => SOURCES[s] || s).join(', ')
}

// The API's fit level ('strong', 'good', 'possible'); its thresholds stay in the backend.
export function fitLabel(fit) {
  return `${capitalise(fit)} match`
}

export function capitalise(text) {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// Filter chip options for the domains in a list of recommendations, largest first.
export function domainOptions(recommendations) {
  const counts = new Map()
  for (const r of recommendations) counts.set(r.domain, (counts.get(r.domain) || 0) + 1)
  const domains = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  return [
    { value: 'all', label: 'All', count: recommendations.length },
    ...domains.map(([domain, count]) => ({ value: domain, label: capitalise(domain), count })),
  ]
}

// Recommendations in the chosen domain whose title, reason or matched skills contain the query.
export function filterRecommendations(recommendations, domain, query) {
  const q = query.trim().toLowerCase()
  const found = (r) =>
    [r.title, r.reason, ...r.matched_skills.flatMap((s) => [s.label, s.query])].some((t) => t.toLowerCase().includes(q))
  return recommendations.filter((r) => (domain === 'all' || r.domain === domain) && (!q || found(r)))
}

// For the history screen: a snapshot time, and how a career moved since the previous snapshot.
export function when(timestamp) {
  return new Date(timestamp).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

// "Up 2", "Down 1", "Same place" or "New" against the previous snapshot.
export function movement(rank, previousRank) {
  if (previousRank == null) return { label: 'New', tone: 'ok' }
  if (previousRank === rank) return { label: 'Same place', tone: 'neutral' }
  const moved = previousRank - rank
  return moved > 0 ? { label: `Up ${moved}`, tone: 'ok' } : { label: `Down ${-moved}`, tone: 'warn' }
}

// What to call the user: their first name when they gave one, or their username.
export function displayName(user) {
  return (user.name ?? '').trim().split(/\s+/)[0] || user.username
}

// Roadmap progress ([{ status }]) counted by status; skills still to do are not stored.
export function planCounts(progress) {
  const done = progress.filter((p) => p.status === 'done').length
  return { learning: progress.length - done, done }
}

// The careers list's filter named in an address (?show=saved), or 'all' when it names none.
export function showFilter(value) {
  return ['matched', 'saved'].includes(value) ? value : 'all'
}

// Careers under the chosen filter and domain whose title or description contains the query.
export function filterCareers(careers, show, domain, query) {
  const q = query.trim().toLowerCase()
  return careers.filter(
    (c) =>
      (show === 'all' || (show === 'matched' ? c.match : c.saved)) &&
      (domain === 'all' || c.domain === domain) &&
      (!q || c.title.toLowerCase().includes(q) || c.description.toLowerCase().includes(q)),
  )
}

// Whether the typed name or email differs from what the account holds.
export function accountChanged(account, name, email) {
  return name.trim() !== (account.name ?? '') || email.trim() !== (account.email ?? '')
}

// A skill's place in a plan. "To do" is the default and is not stored.
export const PLAN_STATUSES = [
  { value: 'todo', label: 'To do' },
  { value: 'learning', label: 'Learning' },
  { value: 'done', label: 'Done' },
]

// { skill id: status } from the stored progress ([{ skill_id, status }]).
export function statusMap(progress) {
  return Object.fromEntries(progress.map((p) => [p.skill_id, p.status]))
}

// Careers worth planning for: saved ones first, then top matches not already listed.
// Each is { career_code, title, domain, rank, saved }; rank is null for a career that is not a match.
export function planCareers(saved, recommendations) {
  const fromSaved = saved.map((c) => ({ career_code: c.career_code, title: c.title, domain: c.domain, rank: c.match?.rank ?? null, saved: true }))
  const listed = new Set(fromSaved.map((c) => c.career_code))
  const fromMatches = recommendations
    .filter((r) => !listed.has(r.career_code))
    .map((r) => ({ career_code: r.career_code, title: r.title, domain: r.domain, rank: r.rank, saved: false }))
  return [...fromSaved, ...fromMatches]
}

// The tabs of a career's page; the first has no address suffix.
export const CAREER_TABS = [
  { value: 'overview', label: 'Overview', suffix: '' },
  { value: 'fit', label: 'Why it fits', suffix: '/fit' },
  { value: 'plan', label: 'Skills plan', suffix: '/plan' },
]
