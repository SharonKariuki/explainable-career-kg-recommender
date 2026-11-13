// Minimal hash router: #/home, #/matches, #/careers/15-2051.00. routes.js says what each address opens.
// Using the URL hash keeps the browser's back button working without a
// routing library.

import { useEffect, useState } from 'react'

export function navigate(path) {
  window.location.hash = path
}

// Like navigate, but replaces the current history entry, so Back skips a moved address.
export function redirect(path) {
  window.location.replace(`#${path}`)
}

export function currentPath() {
  return window.location.hash.replace(/^#/, '') || '/'
}

export function useRoute() {
  const [path, setPath] = useState(currentPath)
  useEffect(() => {
    const onChange = () => setPath(currentPath())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return path
}
