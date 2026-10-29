import { useEffect, useState } from 'react'

import { changePassword, deleteAccount, me, updateAccount } from '../api.js'
import { PageHeader, Pill, Status, ThemeToggle } from '../components.jsx'
import { Icon } from '../icons.jsx'

function Message({ result }) {
  if (!result) return null
  return (
    <p className={`state ${result.ok ? 'ok' : 'error'}`} role={result.ok ? 'status' : 'alert'}>
      <Icon name={result.ok ? 'check' : 'alert'} />
      {result.text}
    </p>
  )
}

export default function SettingsScreen({ theme, onToggleTheme, onSignOut, onDeleted }) {
  const [account, setAccount] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let current = true
    me()
      .then((result) => current && setAccount(result))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  const header = <PageHeader title="Settings" subtitle="Your account, sign-in and appearance." />

  if (!account) return <>{header}<Status loading={!error} error={error} /></>

  return (
    <div className="narrow-page">
      {header}
      <AccountPanel account={account} onChange={setAccount} />
      <PasswordPanel hasPassword={account.has_password} onChanged={() => setAccount({ ...account, has_password: true })} />

      <section className="card panel">
        <div className="ph"><h2>Appearance</h2></div>
        <div className="setting-row">
          <span className="grow">
            <b>{theme === 'dark' ? 'Dark' : 'Light'} theme</b>
            <span className="sub">Saved on this device.</span>
          </span>
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </div>
      </section>

      <section className="card panel">
        <div className="ph"><h2>Session</h2></div>
        <div className="setting-row">
          <span className="grow">
            <b>Sign out</b>
            <span className="sub">Ends your session on this device.</span>
          </span>
          <button type="button" className="btn glass" onClick={onSignOut}><Icon name="logout" />Sign out</button>
        </div>
      </section>

      <DeletePanel username={account.username} onDeleted={onDeleted} />
    </div>
  )
}

function AccountPanel({ account, onChange }) {
  const [email, setEmail] = useState(account.email)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)

  async function save(event) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      onChange({ ...account, ...(await updateAccount(email.trim())) })
      setResult({ ok: true, text: 'Email saved.' })
    } catch (err) {
      setResult({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  const joined = new Date(account.date_joined).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })

  return (
    <section className="card panel">
      <div className="ph"><h2>Account</h2></div>
      <div className="setting-row">
        <span className="av"><Icon name="user" size={16} /></span>
        <span className="grow">
          <b>{account.username}</b>
          <span className="sub">Member since {joined}</span>
        </span>
        {account.google && <Pill>Google sign-in</Pill>}
      </div>
      <form className="stack" onSubmit={save}>
        <label>
          Email
          <input
            className="field"
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              setResult(null)
            }}
            autoComplete="email"
            placeholder="you@example.com"
          />
        </label>
        <Message result={result} />
        <div className="actions">
          <button type="submit" className="btn dark small" disabled={busy || email.trim() === account.email}>
            {busy ? 'Saving…' : 'Save email'}
          </button>
        </div>
      </form>
    </section>
  )
}

function PasswordPanel({ hasPassword, onChanged }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)

  const edit = (setter) => (event) => {
    setter(event.target.value)
    setResult(null)
  }

  async function submit(event) {
    event.preventDefault()
    if (next !== confirm) {
      setResult({ ok: false, text: 'The new passwords do not match.' })
      return
    }
    setBusy(true)
    setResult(null)
    try {
      await changePassword(current, next)
      setCurrent('')
      setNext('')
      setConfirm('')
      setResult({ ok: true, text: hasPassword ? 'Password changed. Other devices have been signed out.' : 'Password set.' })
      onChanged()
    } catch (err) {
      setResult({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card panel">
      <div className="ph"><h2>{hasPassword ? 'Change password' : 'Set a password'}</h2></div>
      {!hasPassword && (
        <p className="muted small">You sign in with Google. A password lets you sign in with your username too.</p>
      )}
      <form className="stack" onSubmit={submit}>
        {hasPassword && (
          <label>
            Current password
            <input className="field" type="password" value={current} onChange={edit(setCurrent)} autoComplete="current-password" required />
          </label>
        )}
        <label>
          New password
          <input className="field" type="password" value={next} onChange={edit(setNext)} autoComplete="new-password" required />
        </label>
        <label>
          Confirm new password
          <input className="field" type="password" value={confirm} onChange={edit(setConfirm)} autoComplete="new-password" required />
        </label>
        <Message result={result} />
        <div className="actions">
          <button type="submit" className="btn dark small" disabled={busy}>
            {busy ? 'Saving…' : hasPassword ? 'Change password' : 'Set password'}
          </button>
        </div>
      </form>
    </section>
  )
}

function DeletePanel({ username, onDeleted }) {
  const [open, setOpen] = useState(false)
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function remove(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await deleteAccount(confirm)
      onDeleted()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <section className="card panel danger-zone">
      <div className="ph"><h2>Delete account</h2></div>
      <p className="muted small">
        Permanently removes your account, skills, saved careers and roadmap progress. This cannot be undone.
      </p>
      {open ? (
        <form className="stack" onSubmit={remove}>
          <label>
            <span>Type <b>{username}</b> to confirm</span>
            <input
              className="field"
              value={confirm}
              onChange={(e) => {
                setConfirm(e.target.value)
                setError(null)
              }}
              autoComplete="off"
            />
          </label>
          {error && <Message result={{ ok: false, text: error }} />}
          <div className="actions">
            <button type="submit" className="btn danger small" disabled={busy || confirm !== username}>
              {busy ? 'Deleting…' : 'Delete my account'}
            </button>
            <button type="button" className="btn glass" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <div className="actions">
          <button type="button" className="btn danger-outline small" onClick={() => setOpen(true)}>Delete account…</button>
        </div>
      )}
    </section>
  )
}
