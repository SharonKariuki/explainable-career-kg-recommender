import { useEffect, useRef, useState } from 'react'

import { googleLogin, login, register } from '../api.js'

// Google sign-in shows only when frontend/.env sets VITE_GOOGLE_CLIENT_ID.
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

let googleScript = null

// Google Identity Services, loaded once and only on the sign-in screen.
function loadGoogle() {
  googleScript ??= new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = () => resolve(window.google)
    script.onerror = () => {
      googleScript = null
      reject(new Error('Could not reach Google. Check your connection and try again.'))
    }
    document.head.append(script)
  })
  return googleScript
}

// Google draws its own button; it hands back an ID token for the API to check.
function GoogleButton({ text, onCredential, onError }) {
  const slot = useRef(null)
  const latest = useRef({ onCredential, onError })
  useEffect(() => {
    latest.current = { onCredential, onError }
  })

  useEffect(() => {
    let cancelled = false
    loadGoogle()
      .then((google) => {
        if (cancelled || !slot.current) return
        google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => latest.current.onCredential(response.credential),
        })
        google.accounts.id.renderButton(slot.current, {
          theme: 'outline',
          size: 'large',
          shape: 'pill',
          text,
          width: Math.min(400, slot.current.offsetWidth),
        })
      })
      .catch((err) => !cancelled && latest.current.onError(err.message))
    return () => {
      cancelled = true
    }
  }, [text])

  return <div ref={slot} className="google-btn" />
}

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

  async function signInWithGoogle(credential) {
    setBusy(true)
    setError(null)
    try {
      onSignedIn(await googleLogin(credential))
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
      {GOOGLE_CLIENT_ID && (
        <>
          <p className="auth-divider muted">or</p>
          <GoogleButton
            text={isRegister ? 'signup_with' : 'signin_with'}
            onCredential={signInWithGoogle}
            onError={setError}
          />
        </>
      )}
      <p className="muted">
        {isRegister ? 'Already have an account?' : 'New here?'}{' '}
        <button type="button" className="link" onClick={switchMode}>
          {isRegister ? 'Sign in' : 'Create an account'}
        </button>
      </p>
    </section>
  )
}
