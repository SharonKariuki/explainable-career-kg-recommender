// Minimal hash router: #/dashboard, #/recommendations, #/careers/15-2051.00.
// Using the URL hash keeps the browser's back button working without a
// routing library.

import { useEffect, useState } from 'react'

export function navigate(path) {
  window.location.hash = path
}

function currentPath() {
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
