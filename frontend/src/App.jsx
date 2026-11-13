import { useEffect, useState } from 'react'

import { SIGNED_OUT_EVENT, getToken, logout, me } from './api.js'
import { Status, ThemeToggle, WakingNotice } from './components.jsx'
import { Icon } from './icons.jsx'
import { currentPath, navigate, redirect, useRoute } from './router.js'
import { activeLink, landing, queryOf, resolve } from './routes.js'
import { useTheme } from './theme.js'
import { TopBar } from './TopBar.jsx'
import AuthScreen from './screens/AuthScreen.jsx'
import CareerDetailScreen from './screens/CareerDetailScreen.jsx'
import CareersScreen from './screens/CareersScreen.jsx'
import DashboardScreen from './screens/DashboardScreen.jsx'
import HistoryScreen from './screens/HistoryScreen.jsx'
import NotFoundScreen from './screens/NotFoundScreen.jsx'
import ProfileScreen from './screens/ProfileScreen.jsx'
import RecommendationsScreen from './screens/RecommendationsScreen.jsx'
import RoadmapScreen from './screens/RoadmapScreen.jsx'
import SettingsScreen from './screens/SettingsScreen.jsx'

// The top bar's pills (wide screens) and the floating tab bar (phones) share these.
const NAV = [
  { path: '/home', label: 'Home', icon: 'home' },
  { path: '/matches', label: 'Matches', icon: 'matches' },
  { path: '/careers', label: 'Careers', icon: 'explore' },
  { path: '/plan', label: 'My plan', icon: 'roadmap' },
]

// Reached from the avatar menu, at every width.
const MORE_NAV = [
  { path: '/profile', label: 'My profile', icon: 'user' },
  { path: '/history', label: 'History', icon: 'matches' },
  { path: '/settings', label: 'Settings', icon: 'settings' },
]

// True once the page has scrolled, when the top bar leaves the navy wash.
function useScrolled() {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return scrolled
}

function App() {
  const address = useRoute()
  const route = resolve(address)
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(Boolean(getToken()))
  const [startupError, setStartupError] = useState(null)
  const [signedOutNotice, setSignedOutNotice] = useState(null)
  const [theme, toggleTheme] = useTheme()
  const scrolled = useScrolled()

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
    // Signing in returns only the username; fetch the rest (the name) for the greeting.
    me().then(setUser).catch(() => {})
    // Open the address that was asked for before signing in, if it is a real page.
    navigate(landing(currentPath()))
  }

  // A moved address is swapped for its new one, so Back does not return to it.
  useEffect(() => {
    if (route.redirect) redirect(route.redirect)
  }, [route.redirect])

  const hasUser = Boolean(user)
  useEffect(() => {
    document.title = hasUser && route.title ? `${route.title} · AjiraGuide` : 'AjiraGuide'
  }, [hasUser, route.title])

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

  const { name, params } = route
  let screen
  if (route.redirect) screen = <Status loading />
  else if (name === 'home') screen = <DashboardScreen user={user} />
  else if (name === 'profile') screen = <ProfileScreen onSaved={() => navigate('/matches')} />
  else if (name === 'matches') screen = <RecommendationsScreen />
  else if (name === 'careers') screen = <CareersScreen show={queryOf(address).show} />
  else if (name === 'career') screen = <CareerDetailScreen key={params.code} code={params.code} />
  else if (name === 'plan') screen = <RoadmapScreen code={params.code} />
  else if (name === 'history') screen = <HistoryScreen key={params.runId ?? 'all'} runId={params.runId} />
  else if (name === 'settings') {
    screen = <SettingsScreen onAccount={setUser} theme={theme} onToggleTheme={toggleTheme} onSignOut={signOut} onDeleted={accountDeleted} />
  }
  else screen = <NotFoundScreen />

  const active = activeLink(address, [...NAV, ...MORE_NAV])
  const current = (n) => (n.path === active ? 'page' : undefined)
  // On phones the round middle button opens the profile, where skills are added.
  const tabs = [NAV[0], NAV[1], { ...MORE_NAV[0], icon: 'plus' }, NAV[2], NAV[3]]

  return (
    <div className={name === 'home' ? 'app on-hero' : 'app'}>
      <TopBar nav={NAV} more={MORE_NAV} active={active} user={user} theme={theme} onToggleTheme={toggleTheme} onSignOut={signOut} stuck={scrolled} />

      <main className="content">
        <WakingNotice />
        {screen}
      </main>

      <nav className="tabs glass" aria-label="Main">
        {tabs.map((n, i) =>
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
