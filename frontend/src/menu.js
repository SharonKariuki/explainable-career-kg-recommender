// Which menu item an arrow, Home or End key moves to; null for any other key.
export function menuTarget(key, index, count) {
  if (key === 'ArrowDown') return (index + 1) % count
  if (key === 'ArrowUp') return (index - 1 + count) % count
  if (key === 'Home') return 0
  if (key === 'End') return count - 1
  return null
}
