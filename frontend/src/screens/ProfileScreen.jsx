import { useEffect, useState } from 'react'

import { getProfile, saveProfile } from '../api.js'

const MAX_SKILLS = 30

export default function ProfileScreen({ onSaved }) {
  const [skills, setSkills] = useState([])
  const [draft, setDraft] = useState('')
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)

  useEffect(() => {
    // Ignore a response that arrives after this effect was cleaned up, or a
    // late load would overwrite skills the user has started adding.
    let current = true
    getProfile()
      .then((profile) => current && setSkills(profile.skills))
      .catch((err) => current && setError(err.message))
      .finally(() => current && setStatus('ready'))
    return () => {
      current = false
    }
  }, [])

  function addSkill(event) {
    event.preventDefault()
    const skill = draft.trim()
    if (!skill) return
    if (skills.some((s) => s.toLowerCase() === skill.toLowerCase())) {
      setError(`"${skill}" is already in your list.`)
      return
    }
    if (skills.length >= MAX_SKILLS) {
      setError(`You can list up to ${MAX_SKILLS} skills.`)
      return
    }
    setSkills([...skills, skill])
    setDraft('')
    setError(null)
  }

  function removeSkill(skill) {
    setSkills(skills.filter((s) => s !== skill))
  }

  async function save() {
    setStatus('saving')
    setError(null)
    try {
      const profile = await saveProfile(skills)
      setSkills(profile.skills)
      onSaved()
    } catch (err) {
      setError(err.message)
      setStatus('ready')
    }
  }

  if (status === 'loading') return <p className="muted">Loading your profile…</p>

  return (
    <section className="card">
      <h1>Your skills</h1>
      <p className="muted">
        List the skills you have, in your own words: tools (Python, Excel), topics (statistics) or
        things you do well (talking to customers). Three or more give better results.
      </p>

      <form onSubmit={addSkill} className="row">
        <label className="grow">
          <span className="visually-hidden">Add a skill</span>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="e.g. SQL"
            maxLength={100}
          />
        </label>
        <button type="submit" className="secondary">Add</button>
      </form>

      {skills.length ? (
        <ul className="chips" aria-label="Your skills">
          {skills.map((skill) => (
            <li key={skill} className="chip">
              {skill}
              <button type="button" className="chip-remove" onClick={() => removeSkill(skill)} aria-label={`Remove ${skill}`}>
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">No skills yet. Add your first one above.</p>
      )}

      {error && <p className="error" role="alert">{error}</p>}

      <div className="actions">
        <button type="button" onClick={save} disabled={!skills.length || status === 'saving'}>
          {status === 'saving' ? 'Saving…' : 'Save and see my careers'}
        </button>
      </div>
    </section>
  )
}
