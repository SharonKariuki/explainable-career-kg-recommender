import { useEffect, useState } from 'react'

import { SIGNED_OUT_EVENT, getToken, logout, me } from './api.js'
import { IconButton, LogoTile, Status, ThemeToggle, WakingNotice } from './components.jsx'
import { Icon } from './icons.jsx'
import { navigate, useRoute } from './router.js'
import { useTheme } from './theme.js'
import AuthScreen from './screens/AuthScreen.jsx'
import CareerDetailScreen from './screens/CareerDetailScreen.jsx'
import CareersScreen from './screens/CareersScreen.jsx'
import DashboardScreen from './screens/DashboardScreen.jsx'
import HistoryScreen from './screens/HistoryScreen.jsx'
import ProfileScreen from './screens/ProfileScreen.jsx'
import RecommendationsScreen from './screens/RecommendationsScreen.jsx'
import RoadmapScreen from './screens/RoadmapScreen.jsx'
import SavedScreen from './screens/SavedScreen.jsx'
import SettingsScreen from './screens/SettingsScreen.jsx'

const CAREER_ROUTE = /^\/careers\/([\w.-]+)$/
const ROADMAP_ROUTE = /^\/roadmap(?:\/([\w.-]+))?$/
const HISTORY_ROUTE = /^\/history(?:\/(\d+))?$/

// The sidebar (wide screens) and the floating tab bar (phones) share these;
// on phones the middle one is the round black button.
const NAV = [
  { path: '/dashboard', label: 'Home', icon: 'home' },
  { path: '/recommendations', label: 'Matches', icon: 'matches' },
  { path: '/assessment', label: 'Your skills', icon: 'plus' },
  { path: '/careers', label: 'Explore', icon: 'explore' },
  { path: '/roadmap', label: 'Roadmap', icon: 'roadmap' },
]

// Sidebar only; on phones they are reached from the dashboard.
const MORE_NAV = [
  { path: '/saved', label: 'Saved', icon: 'bookmark' },
  { path: '/history', label: 'History', icon: 'matches' },
  { path: '/settings', label: 'Settings', icon: 'settings' },
]

function initials(name) {
  return name.slice(0, 2).toUpperCase()
}

function App() {
  const route = useRoute()
  const path = route === '/profile' ? '/assessment' : route  // the old address still works
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(Boolean(getToken()))
  const [startupError, setStartupError] = useState(null)
  const [signedOutNotice, setSignedOutNotice] = useState(null)
  const [theme, toggleTheme] = useTheme()

  // A saved token may have expired or been revoked; confirm it on load. Only a
  // 401 means signed out: a network error or a sleeping server keeps the token.
  useEffect(() => {
    if (!getToken()) return
    me()
      .then(setUser)
      .catch((err) => (err.status === 401 ? setUser(null) : setStartupError(err.message)))
      .finally(() => setChecking(false))
  }, [])

  // Any request answered 401 (expired or revoked token) returns to sign-in.
  useEffect(() => {
    const onSignedOut = () => {
      setUser(null)
      setSignedOutNotice('Your session has ended. Please sign in again.')
      navigate('/')
    }
    window.addEventListener(SIGNED_OUT_EVENT, onSignedOut)
    return () => window.removeEventListener(SIGNED_OUT_EVENT, onSignedOut)
  }, [])

  async function signOut() {
    await logout()
    setUser(null)
    navigate('/')
  }

  function accountDeleted() {
    setUser(null)
    navigate('/')
  }

  function signedIn(account) {
    setSignedOutNotice(null)
    setUser(account)
    navigate('/dashboard')
  }

  if (checking) return <main className="auth"><WakingNotice /><Status loading /></main>
  if (startupError) return <main className="auth"><Status error={startupError} /></main>
  if (!user) {
    return (
      <main className="auth">
        <WakingNotice />
        <ThemeToggle theme={theme} onToggle={toggleTheme} className="auth-theme" />
        <AuthScreen onSignedIn={signedIn} notice={signedOutNotice} />
      </main>
    )
  }

  const career = path.match(CAREER_ROUTE)
  const roadmap = path.match(ROADMAP_ROUTE)
  const historyRoute = path.match(HISTORY_ROUTE)
  let screen
  if (path === '/assessment') screen = <ProfileScreen onSaved={() => navigate('/recommendations')} />
  else if (path === '/recommendations') screen = <RecommendationsScreen />
  else if (path === '/careers') screen = <CareersScreen />
  else if (career) screen = <CareerDetailScreen key={career[1]} code={career[1]} />
  else if (roadmap) screen = <RoadmapScreen code={roadmap[1]} />
  else if (path === '/saved') screen = <SavedScreen />
  else if (historyRoute) screen = <HistoryScreen key={historyRoute[1] ?? 'all'} runId={historyRoute[1]} />
  else if (path === '/settings') {
    screen = <SettingsScreen theme={theme} onToggleTheme={toggleTheme} onSignOut={signOut} onDeleted={accountDeleted} />
  }
  else screen = <DashboardScreen user={user} onSignOut={signOut} theme={theme} onToggleTheme={toggleTheme} />

  const active = [...NAV, ...MORE_NAV].find((n) => path.startsWith(n.path))?.path ?? '/dashboard'
  const current = (n) => (n.path === active ? 'page' : undefined)

  return (
    <div className="app">
      <aside className="sidebar glass">
        <a href="#/dashboard" className="brand">
          <LogoTile size={36} />
          AjiraGuide
        </a>
        <nav aria-label="Main">
          {NAV.map((n) => (
            <a key={n.path} href={`#${n.path}`} aria-current={current(n)}>
              <Icon name={n.icon} />
              {n.label}
            </a>
          ))}
          <hr className="nav-rule" />
          {MORE_NAV.map((n) => (
            <a key={n.path} href={`#${n.path}`} aria-current={current(n)}>
              <Icon name={n.icon} />
              {n.label}
            </a>
          ))}
        </nav>
        <div className="sidebar-user">
          <span className="av">{initials(user.username)}</span>
          <a className="grow truncate" href="#/settings" title="Settings">{user.username}</a>
          <ThemeToggle theme={theme} onToggle={toggleTheme} glass={false} />
          <IconButton icon="logout" label="Sign out" onClick={signOut} glass={false} />
        </div>
      </aside>

      <main className="content">
        <WakingNotice />
        {screen}
      </main>

      <nav className="tabs glass" aria-label="Main">
        {NAV.map((n, i) =>
          i === 2 ? (
            <a key={n.path} href={`#${n.path}`} className="tab-plus" aria-label={n.label} aria-current={current(n)}>
              <Icon name={n.icon} size={20} />
            </a>
          ) : (
            <a key={n.path} href={`#${n.path}`} className="tab" aria-current={current(n)}>
              <Icon name={n.icon} />
              {n.label}
            </a>
          ),
        )}
      </nav>
    </div>
  )
}

export default App
