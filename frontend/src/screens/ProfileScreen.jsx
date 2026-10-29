import { useEffect, useState } from 'react'

import { getProfile, saveProfile } from '../api.js'
import { PageHeader, Progress, Status } from '../components.jsx'
import { Icon } from '../icons.jsx'

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

  const header = (
    <PageHeader
      title="Your skills"
      subtitle="List the skills you have, in your own words: tools (Python, Excel), topics (statistics) or things you do well (talking to customers). Three or more give better results."
    />
  )

  if (status === 'loading') return <>{header}<Status loading /></>

  return (
    <div className="narrow-page">
      {header}

      <form onSubmit={addSkill} className="search glass add-skill">
        <Icon name="plus" size={17} />
        <label className="grow">
          <span className="visually-hidden">Add a skill</span>
          <input
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value)
              setError(null)
            }}
            placeholder="Add a skill, e.g. SQL"
            maxLength={100}
          />
        </label>
        <button type="submit" className="btn small dark" disabled={!draft.trim()}>Add</button>
      </form>

      {error && <p className="field-error" role="alert">{error}</p>}

      <section className="card panel">
        <div className="ph">
          <p className="mono">Skills in profile</p>
          <span className="num">{skills.length} of {MAX_SKILLS}</span>
        </div>
        <Progress value={skills.length / MAX_SKILLS} label={`${skills.length} of ${MAX_SKILLS} skills listed`} />
        {skills.length ? (
          <ul className="chips" aria-label="Your skills">
            {skills.map((skill) => (
              <li key={skill} className="chip">
                {skill}
                <button type="button" className="chip-remove" onClick={() => removeSkill(skill)} aria-label={`Remove ${skill}`}>
                  <Icon name="close" size={14} />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty">No skills yet. Add your first one above.</p>
        )}
      </section>

      <div className="actions">
        <button type="button" className="btn primary" onClick={save} disabled={!skills.length || status === 'saving'}>
          {status === 'saving' ? 'Saving…' : 'Save and see my careers'}
        </button>
      </div>
    </div>
  )
}
