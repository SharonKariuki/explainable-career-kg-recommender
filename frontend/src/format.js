// Formatting helpers shared by the recommendation screens.

const SOURCES = { onet_skill: 'O*NET rating', onet_tool: 'O*NET tools', esco: 'ESCO' }

export function sourceNames(sources) {
  return sources.map((s) => SOURCES[s] || s).join(', ')
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

// Recommendations in the chosen domain whose title or summary contains the query.
export function filterRecommendations(recommendations, domain, query) {
  const q = query.trim().toLowerCase()
  return recommendations.filter(
    (r) =>
      (domain === 'all' || r.domain === domain) &&
      (!q || r.title.toLowerCase().includes(q) || r.summary.toLowerCase().includes(q)),
  )
}
