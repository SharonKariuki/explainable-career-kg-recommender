import { useEffect, useState } from 'react'

import { getToken, logout, me } from './api.js'
import { navigate, useRoute } from './router.js'
import AuthScreen from './screens/AuthScreen.jsx'
import ProfileScreen from './screens/ProfileScreen.jsx'

function App() {
  const path = useRoute()
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(Boolean(getToken()))

  // A saved token may have expired or been revoked; confirm it on load.
  useEffect(() => {
    if (!getToken()) return
    me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false))
  }, [])

  async function signOut() {
    await logout()
    setUser(null)
    navigate('/')
  }

  function signedIn(account) {
    setUser(account)
    navigate('/profile')
  }

  let screen
  if (checking) screen = <p className="muted">Loading…</p>
  else if (!user) screen = <AuthScreen onSignedIn={signedIn} />
  else screen = <ProfileScreen onSaved={() => navigate('/recommendations')} />

  return (
    <>
      <header className="site-header">
        <a href="#/" className="brand">AjiraGuide</a>
        {user && (
          <nav aria-label="Main">
            <a href="#/profile" aria-current={path === '/profile' ? 'page' : undefined}>My skills</a>
            <span className="muted">{user.username}</span>
            <button type="button" className="link" onClick={signOut}>Sign out</button>
          </nav>
        )}
      </header>
      <main>{screen}</main>
    </>
  )
}

export default App
