// Warm Glass building blocks shared by the screens. Glass is for controls,
// white cards for reading, and each screen has at most one black hero card.

import { useState } from 'react'

import { saveCareer, unsaveCareer } from './api.js'
import { Icon } from './icons.jsx'

export function LogoTile({ size = 42 }) {
  return (
    <span className="logo-tile" style={{ '--size': `${size}px` }} aria-hidden="true">A</span>
  )
}

export function PageHeader({ title, subtitle, back, children }) {
  return (
    <header className="page-header">
      {back && (
        <a className="back-link glass" href={back.href}>
          <Icon name="back" size={16} />
          {back.label}
        </a>
      )}
      <div className="page-header-row">
        <div>
          <h1>{title}</h1>
          {subtitle && <p className="subtitle">{subtitle}</p>}
        </div>
        {children}
      </div>
    </header>
  )
}

// glass={false} gives the quieter borderless variant used inside the sidebar.
export function IconButton({ icon, label, onClick, href, glass = true, className = '' }) {
  const classes = `icon-btn ${glass ? 'glass' : 'plain'} ${className}`
  if (href) {
    return (
      <a className={classes} href={href} aria-label={label} title={label}>
        <Icon name={icon} />
      </a>
    )
  }
  return (
    <button type="button" className={classes} onClick={onClick} aria-label={label} title={label}>
      <Icon name={icon} />
    </button>
  )
}

export function ThemeToggle({ theme, onToggle, glass, className }) {
  const dark = theme === 'dark'
  return (
    <IconButton
      icon={dark ? 'sun' : 'moon'}
      label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      onClick={onToggle}
      glass={glass}
      className={className}
    />
  )
}

export function SearchField({ label, value, onChange, placeholder }) {
  return (
    <label className="search glass">
      <Icon name="search" size={17} />
      <span className="visually-hidden">{label}</span>
      <input type="search" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </label>
  )
}

// options: [{ value, label, count }]; the active chip turns black.
export function FilterChips({ label, options, value, onChange }) {
  return (
    <div className="filters" role="group" aria-label={label}>
      {options.map((o) => {
        const on = o.value === value
        return (
          <button key={o.value} type="button" className={on ? 'filter on' : 'filter glass'} aria-pressed={on} onClick={() => onChange(o.value)}>
            {o.label}
            <em className="num">{o.count}</em>
          </button>
        )
      })}
    </div>
  )
}

// tone: ok, warn, danger, or neutral for plain labels such as a requirement level.
export function Pill({ tone = 'neutral', children }) {
  return <span className={`pill ${tone}`}>{children}</span>
}

export function Notice({ icon = 'bulb', title, children, action }) {
  return (
    <div className="notice">
      <i className="notice-icon"><Icon name={icon} size={17} /></i>
      <div className="grow">
        <b>{title}</b>
        {children && <span>{children}</span>}
      </div>
      {action && (
        <a className="notice-action" href={action.href}>
          {action.label}
          <Icon name="forward" size={14} />
        </a>
      )}
    </div>
  )
}

export function Kpi({ label, value, note }) {
  return (
    <div className="card kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value num">{value}</div>
      <div className="kpi-note">{note}</div>
    </div>
  )
}

// A 0-1 fill. Gold marks progress or what is current; dark is for plain amounts.
export function Progress({ value, tone = 'dark', label }) {
  const percent = Math.round(Math.max(0, Math.min(1, value)) * 100)
  return (
    <div className={`progress ${tone}`} role="img" aria-label={label}>
      <span style={{ width: `${percent}%` }} />
    </div>
  )
}

export function Meter({ label, value, weight }) {
  return (
    <div className="meter">
      <div className="meter-label">
        <span>{label}{weight !== undefined && <span className="muted"> · weight {Math.round(weight * 100)}%</span>}</span>
        <span className="num">{value.toFixed(2)}</span>
      </div>
      <Progress value={value} label={`${label} ${value.toFixed(2)} out of 1`} />
    </div>
  )
}

export function Status({ loading, error }) {
  if (loading) {
    return (
      <p className="state" role="status">
        <span className="spinner" aria-hidden="true" />
        Loading…
      </p>
    )
  }
  if (error) {
    return (
      <p className="state error" role="alert">
        <Icon name="alert" />
        {error}
      </p>
    )
  }
  return null
}

export function EmptyState({ title, children, action }) {
  return (
    <section className="card empty-state">
      <h2>{title}</h2>
      {children && <p className="muted">{children}</p>}
      {action && <a className="btn primary" href={action.href}>{action.label}</a>}
    </section>
  )
}

// Bookmarks a career. The button flips at once and flips back if the request fails.
export function SaveButton({ code, saved: initial, onChange, compact = false }) {
  const [saved, setSaved] = useState(initial)
  const [busy, setBusy] = useState(false)

  async function toggle() {
    const next = !saved
    setSaved(next)
    setBusy(true)
    try {
      await (next ? saveCareer(code) : unsaveCareer(code))
      onChange?.(next)
    } catch {
      setSaved(!next)
    } finally {
      setBusy(false)
    }
  }

  const label = saved ? 'Saved' : 'Save'
  return (
    <button
      type="button"
      className={`btn ${compact ? 'small' : ''} ${saved ? 'dark' : 'glass'} save-btn`}
      onClick={toggle}
      disabled={busy}
      aria-pressed={saved}
      aria-label={compact ? `${saved ? 'Unsave' : 'Save'} this career` : undefined}
      title={saved ? 'Remove from saved careers' : 'Save this career'}
    >
      <Icon name="bookmark" size={16} />
      {label}
    </button>
  )
}

// Choose one of a few options, such as a skill's roadmap status.
export function Segmented({ label, options, value, onChange, disabled }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          className={o.value === value ? 'on' : ''}
          onClick={() => o.value !== value && onChange(o.value)}
          disabled={disabled}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
