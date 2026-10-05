// Formatting helpers shared by the recommendation screens.

const SOURCES = { onet_skill: 'O*NET rating', onet_tool: 'O*NET tools', esco: 'ESCO' }

export function sourceNames(sources) {
  return sources.map((s) => SOURCES[s] || s).join(', ')
}
