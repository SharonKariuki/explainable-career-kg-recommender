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
