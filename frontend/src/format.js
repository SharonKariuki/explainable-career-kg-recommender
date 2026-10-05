// Formatting helpers shared by the recommendation screens.

// Same bands the explanation generator uses (backend recommender/explanation.py).
export function requirementLevel(edgeWeight) {
  if (edgeWeight >= 0.75) return 'Core requirement'
  if (edgeWeight >= 0.5) return 'Important'
  return 'Supporting'
}

const SOURCES = { onet_skill: 'O*NET rating', onet_tool: 'O*NET tools', esco: 'ESCO' }

export function sourceNames(sources) {
  return sources.map((s) => SOURCES[s] || s).join(', ')
}
