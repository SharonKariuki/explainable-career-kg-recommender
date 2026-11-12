// The top bar shown on every signed-in screen: logo, the main links as pills,
// and the avatar menu holding the account links, the theme toggle and sign-out.

import { useEffect, useId, useRef, useState } from 'react'

import { LogoTile } from './components.jsx'
import { Icon } from './icons.jsx'
import { menuTarget } from './menu.js'

function initials(name) {
  return name.slice(0, 2).toUpperCase()
}

// links: [{ path, label, icon }]. The button opens a menu: arrows, Home and End
// move through it, Escape or Tab closes it, and focus returns to the button.
export function AvatarMenu({ username, links, active, theme, onToggleTheme, onSignOut }) {
  const [open, setOpen] = useState(false)
  const [focusLast, setFocusLast] = useState(false)
  const root = useRef(null)
  const button = useRef(null)
  const menu = useRef(null)
  const menuId = useId()
  const dark = theme === 'dark'

  const items = () => [...menu.current.querySelectorAll('[role="menuitem"]')]

  function close(refocus = true) {
    setOpen(false)
    if (refocus) button.current?.focus()
  }

  function openAt(last) {
    setFocusLast(last)
    setOpen(true)
  }

  // Opening puts focus on the first item, or the last when opened with the up arrow.
  useEffect(() => {
    if (!open) return
    const all = items()
    all[focusLast ? all.length - 1 : 0]?.focus()
  }, [open, focusLast])

  // A press outside closes the menu. Focus goes back to the avatar unless the
  // press landed on another control, which keeps the focus it just took.
  useEffect(() => {
    if (!open) return
    const onPress = (event) => {
      if (root.current.contains(event.target)) return
      setOpen(false)
      if (event.target.closest?.('a, button, input, select, textarea, summary, [tabindex]')) return
      // Wait for the press to finish: it blurs whatever had focus.
      setTimeout(() => button.current?.focus())
    }
    document.addEventListener('pointerdown', onPress)
    return () => document.removeEventListener('pointerdown', onPress)
  }, [open])

  function onButtonKey(event) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      openAt(event.key === 'ArrowUp')
    }
  }

  function onMenuKey(event) {
    if (event.key === 'Escape') {
      event.preventDefault()
      close()
      return
    }
    // Tab leaves the menu: focus steps back to the avatar and the browser moves on from there.
    if (event.key === 'Tab') {
      close()
      return
    }
    const all = items()
    const target = menuTarget(event.key, all.indexOf(document.activeElement), all.length)
    if (target === null) return
    event.preventDefault()
    all[target].focus()
  }

  const onAccountPage = links.some((l) => l.path === active)

  return (
    <div className="avatar-menu" ref={root}>
      <button
        type="button"
        ref={button}
        className={onAccountPage ? 'avatar-btn glass on' : 'avatar-btn glass'}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={`Account menu for ${username}`}
        onClick={() => (open ? close() : openAt(false))}
        onKeyDown={onButtonKey}
      >
        <span className="av">{initials(username)}</span>
        <Icon name="chevron" size={15} />
      </button>
      {open && (
        <div className="menu" id={menuId} role="menu" aria-label="Account" ref={menu} onKeyDown={onMenuKey}>
          <p className="menu-user truncate" role="presentation">{username}</p>
          {links.map((l) => (
            <a
              key={l.path}
              href={`#${l.path}`}
              role="menuitem"
              tabIndex={-1}
              aria-current={l.path === active ? 'page' : undefined}
              onClick={() => close()}
            >
              <Icon name={l.icon} />
              {l.label}
            </a>
          ))}
          <hr role="separator" />
          <button type="button" role="menuitem" tabIndex={-1} onClick={() => { onToggleTheme(); close() }}>
            <Icon name={dark ? 'sun' : 'moon'} />
            {dark ? 'Light mode' : 'Dark mode'}
          </button>
          <button type="button" role="menuitem" tabIndex={-1} onClick={onSignOut}>
            <Icon name="logout" />
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

// nav: the main links; more: the account links. active is the current link's path.
export function TopBar({ nav, more, active, user, theme, onToggleTheme, onSignOut }) {
  return (
    <header className="topbar glass">
      <a href="#/dashboard" className="brand">
        <LogoTile size={36} />
        <span>AjiraGuide</span>
      </a>
      <nav className="topnav" aria-label="Main">
        {nav.map((n) => (
          <a key={n.path} href={`#${n.path}`} title={n.label} aria-current={n.path === active ? 'page' : undefined}>
            <Icon name={n.icon} />
            <span>{n.label}</span>
          </a>
        ))}
      </nav>
      <AvatarMenu
        username={user.username}
        links={more}
        active={active}
        theme={theme}
        onToggleTheme={onToggleTheme}
        onSignOut={onSignOut}
      />
    </header>
  )
}
