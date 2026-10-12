import { useState } from 'react'

import { login, register } from '../api.js'

export default function AuthScreen({ onSignedIn }) {
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const isRegister = mode === 'register'

  // Editing a field clears the last error, which may no longer apply.
  const edit = (setter) => (event) => {
    setter(event.target.value)
    setError(null)
  }

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const user = isRegister ? await register(username, password, email) : await login(username, password)
      onSignedIn(user)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  function switchMode() {
    setMode(isRegister ? 'login' : 'register')
    setError(null)
  }

  return (
    <section className="card narrow">
      <h1>{isRegister ? 'Create your account' : 'Sign in'}</h1>
      <p className="muted">
        AjiraGuide suggests tech careers from the skills you already have, and explains why.
      </p>
      <form onSubmit={submit} className="stack">
        <label>
          Username
          <input value={username} onChange={edit(setUsername)} autoComplete="username" required />
        </label>
        {isRegister && (
          <label>
            Email <span className="muted">(optional)</span>
            <input type="email" value={email} onChange={edit(setEmail)} autoComplete="email" />
          </label>
        )}
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={edit(setPassword)}
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            required
          />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}
        </button>
      </form>
      <p className="muted">
        {isRegister ? 'Already have an account?' : 'New here?'}{' '}
        <button type="button" className="link" onClick={switchMode}>
          {isRegister ? 'Sign in' : 'Create an account'}
        </button>
      </p>
    </section>
  )
}
