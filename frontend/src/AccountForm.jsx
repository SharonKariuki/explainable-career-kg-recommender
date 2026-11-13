// The student's name and email, shown on the profile page and saved on their own.

import { useState } from 'react'

import { updateAccount } from './api.js'
import { accountChanged } from './format.js'
import { Icon } from './icons.jsx'

// account: { username, name, email }. onChange gets the saved account.
export function AccountForm({ account, onChange }) {
  const [email, setEmail] = useState(account.email ?? '')
  const [name, setName] = useState(account.name ?? '')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)

  async function save(event) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      onChange({ ...account, ...(await updateAccount({ name: name.trim(), email: email.trim() })) })
      setResult({ ok: true, text: 'Your details are saved.' })
    } catch (err) {
      setResult({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  const edit = (setter) => (event) => {
    setter(event.target.value)
    setResult(null)
  }

  return (
    <section className="card panel" aria-labelledby="details-heading">
      <div className="ph">
        <p className="mono" id="details-heading">Your details</p>
        <span>Signed in as {account.username}</span>
      </div>
      <p className="muted small">Your name is used to greet you. Both are optional.</p>
      <form className="stack" onSubmit={save}>
        <label>
          Full name
          <input className="field" value={name} onChange={edit(setName)} autoComplete="name" maxLength={150} />
        </label>
        <label>
          Email
          <input className="field" type="email" value={email} onChange={edit(setEmail)} autoComplete="email" placeholder="you@example.com" />
        </label>
        {result && (
          <p className={`state ${result.ok ? 'ok' : 'error'}`} role={result.ok ? 'status' : 'alert'}>
            <Icon name={result.ok ? 'check' : 'alert'} />
            {result.text}
          </p>
        )}
        <div className="actions">
          <button type="submit" className="btn dark small" disabled={busy || !accountChanged(account, name, email)}>
            {busy ? 'Saving…' : 'Save details'}
          </button>
        </div>
      </form>
    </section>
  )
}
