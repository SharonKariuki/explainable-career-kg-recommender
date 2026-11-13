import { useEffect, useState } from 'react'

import { AccountForm } from '../AccountForm.jsx'
import { getProfile, me, saveProfile, searchSkills } from '../api.js'
import { PageHeader, Progress, Status } from '../components.jsx'
import { Icon } from '../icons.jsx'

const MAX_SKILLS = 30
const EDUCATION_LEVELS = [
  ['', 'Choose one (optional)'],
  ['secondary', 'Secondary school'],
  ['certificate', 'Certificate or diploma'],
  ['undergraduate', 'Undergraduate degree (in progress)'],
  ['bachelor', "Bachelor's degree"],
  ['postgraduate', 'Postgraduate degree'],
]
const EMPTY_BACKGROUND = { education_level: '', field_of_study: '', interests: '', experience: '' }
// Wait this long after typing stops before asking for suggestions.
const SUGGEST_DELAY_MS = 200

// onAccount gets the account when the name or email is saved, so the greeting follows.
export default function ProfileScreen({ onSaved, onAccount }) {
  const [skills, setSkills] = useState([])
  const [account, setAccount] = useState(null)
  const [background, setBackground] = useState(EMPTY_BACKGROUND)
  const [draft, setDraft] = useState('')
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [suggestions, setSuggestions] = useState([])

  // Skill names from the knowledge graph that contain what the user is typing.
  useEffect(() => {
    const query = draft.trim()
    if (query.length < 2) return
    let current = true
    const timer = setTimeout(() => {
      searchSkills(query)
        .then((result) => current && setSuggestions(result.results))
        .catch(() => current && setSuggestions([]))
    }, SUGGEST_DELAY_MS)
    return () => {
      current = false
      clearTimeout(timer)
    }
  }, [draft])

  useEffect(() => {
    // Ignore a response that arrives after this effect was cleaned up, or a
    // late load would overwrite skills the user has started adding.
    let current = true
    Promise.all([getProfile(), me()])
      .then(([profile, details]) => {
        if (!current) return
        setAccount(details)
        setSkills(profile.skills)
        setBackground(Object.fromEntries(Object.keys(EMPTY_BACKGROUND).map((k) => [k, profile[k] ?? ''])))
      })
      .catch((err) => current && setError(err.message))
      .finally(() => current && setStatus('ready'))
    return () => {
      current = false
    }
  }, [])

  function addSkill(event) {
    event.preventDefault()
    add(draft.trim())
  }

  function add(skill) {
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
    setSuggestions([])
    setError(null)
  }

  function removeSkill(skill) {
    setSkills(skills.filter((s) => s !== skill))
  }

  async function save() {
    setStatus('saving')
    setError(null)
    try {
      const profile = await saveProfile({ skills, ...background })
      setSkills(profile.skills)
      onSaved()
    } catch (err) {
      setError(err.message)
      setStatus('ready')
    }
  }

  const header = (
    <PageHeader
      title="My profile"
      subtitle="What AjiraGuide knows about you. List your skills in your own words: tools (Python, Excel), topics (statistics) or things you do well (talking to customers). Three or more give better results."
    />
  )

  if (status === 'loading') return <>{header}<Status loading /></>

  return (
    <>
    {header}
    <div className="narrow-page">

      <form onSubmit={addSkill} className="search glass add-skill">
        <Icon name="plus" size={17} />
        <label className="grow">
          <span className="visually-hidden">Add a skill</span>
          <input
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value)
              if (e.target.value.trim().length < 2) setSuggestions([])
              setError(null)
            }}
            placeholder="Add a skill, e.g. SQL"
            maxLength={100}
          />
        </label>
        <button type="submit" className="btn small dark" disabled={!draft.trim()}>Add</button>
      </form>

      {suggestions.length > 0 && draft.trim().length >= 2 && (
        <div className="suggestions">
          <p className="muted small">Skills we know that match “{draft.trim()}”. Pick one, or add your own wording.</p>
          <ul className="chips" aria-label="Suggested skills">
            {suggestions
              .filter((s) => !skills.some((k) => k.toLowerCase() === s.label.toLowerCase()))
              .map((s) => (
                <li key={s.label}>
                  <button type="button" className="chip suggestion" onClick={() => add(s.label)}>
                    <Icon name="plus" size={13} />
                    {s.label}
                    <em className="num" title={`Required by ${s.careers} careers`}>{s.careers}</em>
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}

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

      <section className="card panel about-you">
        <div className="ph">
          <p className="mono">About you (optional)</p>
        </div>
        <p className="muted small">
          What you enjoy, what you study and what you have done. AjiraGuide compares this with each career's
          description and counts it towards your matches. Leave it empty to be matched on skills alone.
        </p>
        <div className="stack">
          <label>
            <span>Education level</span>
            <select className="field" value={background.education_level} onChange={(e) => setBackground({ ...background, education_level: e.target.value })}>
              {EDUCATION_LEVELS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>
            <span>Field of study</span>
            <input
              className="field"
              value={background.field_of_study}
              onChange={(e) => setBackground({ ...background, field_of_study: e.target.value })}
              placeholder="e.g. Computer Science, Statistics"
              maxLength={200}
            />
          </label>
          <label>
            <span>Career interests</span>
            <textarea
              className="field"
              value={background.interests}
              onChange={(e) => setBackground({ ...background, interests: e.target.value })}
              placeholder="e.g. I like solving puzzles with data and explaining what I find to others."
              maxLength={1000}
              rows={3}
            />
          </label>
          <label>
            <span>Work or project experience</span>
            <textarea
              className="field"
              value={background.experience}
              onChange={(e) => setBackground({ ...background, experience: e.target.value })}
              placeholder="e.g. Built a website for a student club; cleaned survey data in Excel for a class project."
              maxLength={2000}
              rows={3}
            />
          </label>
        </div>
      </section>

      <div className="actions">
        <button type="button" className="btn primary" onClick={save} disabled={!skills.length || status === 'saving'}>
          {status === 'saving' ? 'Saving…' : 'Save and see my careers'}
        </button>
      </div>

      {account && <AccountForm account={account} onChange={(next) => { setAccount(next); onAccount?.(next) }} />}
    </div>
    </>
  )
}
