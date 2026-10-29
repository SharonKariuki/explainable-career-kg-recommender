// Light or dark theme. index.html applies the saved choice (or the system
// setting) before the first paint; this hook keeps it in sync after that.

import { useEffect, useState } from 'react'

const THEME_KEY = 'ajiraguide.theme'
const THEME_COLOR = { light: '#efe8e2', dark: '#0a0a0b' }

export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || 'light')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLOR[theme])
  }, [theme])

  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark'
    try {
      localStorage.setItem(THEME_KEY, next)
    } catch {
      // Storage unavailable (private mode): the choice lasts until reload.
    }
    setTheme(next)
  }

  return [theme, toggle]
}
