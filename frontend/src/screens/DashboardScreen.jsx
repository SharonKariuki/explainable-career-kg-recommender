import { useEffect, useState } from 'react'

import { getProgress, getRecommendations, getSaved } from '../api.js'
import { EmptyState, IconButton, Kpi, LogoTile, Notice, Pill, Progress, Status, ThemeToggle } from '../components.jsx'
import { capitalise } from '../format.js'
import { Icon } from '../icons.jsx'

// The skills screen advises three or more skills for better results.
const ADVISED_SKILLS = 3
// The API caps top at 50, above the number of careers, so this ranks them all.
const ALL_CAREERS = 50

const ACTIONS = [
  { href: '#/assessment', label: 'Add skills', icon: 'plus' },
  { href: '#/recommendations', label: 'Matches', icon: 'matches' },
  { href: '#/careers', label: 'Explore', icon: 'explore' },
  { href: '#/roadmap', label: 'Roadmap', icon: 'roadmap' },
]

function greeting(hour) {
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? '' : 's'}`
}

// The single most useful thing to do next, from the profile as it stands.
function nextStep(skillCount, uncertain, top) {
  if (skillCount < ADVISED_SKILLS) {
    return {
      title: `Add ${plural(ADVISED_SKILLS - skillCount, 'more skill')}`,
      text: 'Three or more skills give better results.',
      action: { href: '#/assessment', label: 'Add skills' },
    }
  }
  if (uncertain) {
    return {
      title: `Reword ${plural(uncertain, 'uncertain skill')}`,
      text: 'They had no close match in our data, so they count for less.',
      action: { href: '#/assessment', label: 'Edit skills' },
    }
  }
  if (!top) return null
  return {
    title: `See what to learn for ${top.title}`,
    text: 'Your top match, with the skills it needs that you have not listed.',
    action: { href: `#/roadmap/${top.career_code}`, label: 'Roadmap' },
  }
}

export default function DashboardScreen({ user, onSignOut, theme, onToggleTheme }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [hello] = useState(() => greeting(new Date().getHours()))

  useEffect(() => {
    let current = true
    Promise.all([getRecommendations(ALL_CAREERS), getSaved(), getProgress()])
      .then(([result, saved, progress]) => current && setData({ ...result, saved: saved.careers, progress: progress.skills }))
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [])

  const header = (
    <header className="greet">
      <div className="who">
        <LogoTile />
        <div>
          <p>{hello}</p>
          <h1>{user.username}</h1>
        </div>
      </div>
      {/* On phones there is no sidebar, so its theme and sign-out controls live here. */}
      <div className="greet-actions phone-only">
        <IconButton icon="bookmark" label="Saved careers" href="#/saved" />
        <IconButton icon="settings" label="Settings" href="#/settings" />
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        <IconButton icon="logout" label="Sign out" onClick={onSignOut} />
      </div>
    </header>
  )

  if (!data) return <>{header}<Status loading={!error} error={error} /></>

  if (!data.skills.length) {
    return (
      <>
        {header}
        <EmptyState title="Start with your skills" action={{ href: '#/assessment', label: 'Add your skills' }}>
          List what you can already do, in your own words. AjiraGuide ranks the tech careers that use those skills and
          explains each match.
        </EmptyState>
      </>
    )
  }

  const skillCount = data.skills.length
  const uncertain = data.matches.filter((m) => m.low_confidence).length
  const confident = data.matches.length - uncertain
  const top = data.recommendations.slice(0, 3)
  const next = nextStep(skillCount, uncertain, top[0])
  const learningCount = data.progress.filter((p) => p.status === 'learning').length

  return (
    <>
      {header}
      <div className="dash">
        <div className="dash-col">
          <section className="hero-card" aria-labelledby="hero-label">
            <p className="mono" id="hero-label"><i aria-hidden="true" />Careers linked to your skills</p>
            <div className="hero-figure num">{data.recommendations.length}</div>
            <p className="hero-sub">from the {plural(skillCount, 'skill')} in your profile</p>
            <Progress
              value={data.matches.length ? confident / data.matches.length : 0}
              tone="gold"
              label={`${confident} of ${data.matches.length} skills matched confidently`}
            />
            <div className="hero-foot">
              <span className="num">{confident} of {data.matches.length} matched confidently</span>
              {uncertain > 0 && <span className="num">{uncertain} uncertain</span>}
            </div>
          </section>

          <nav className="acts" aria-label="Quick actions">
            {ACTIONS.map((a) => (
              <a key={a.href} href={a.href} className="act">
                <i className="glass"><Icon name={a.icon} /></i>
                {a.label}
              </a>
            ))}
          </nav>
        </div>

        <div className="dash-col">
          <div className="kpis">
            <Kpi
              label="Skills in profile"
              value={skillCount}
              note={skillCount < ADVISED_SKILLS ? <Pill tone="warn">Below 3</Pill> : '3 or more advised'}
            />
            <Kpi
              label="Uncertain matches"
              value={uncertain}
              note={uncertain ? <Pill tone="warn">Worth rewording</Pill> : <Pill tone="ok">All matched</Pill>}
            />
          </div>
          {next && (
            <Notice title={next.title} action={next.action}>{next.text}</Notice>
          )}
        </div>

        <section className="card panel dash-wide">
          <div className="ph">
            <h2>Top matches</h2>
            <a href="#/recommendations">See all</a>
          </div>
          {top.length ? (
            <ol className="list">
              {top.map((r) => (
                <li key={r.career_code}>
                  <a className="row" href={`#/careers/${r.career_code}`}>
                    <span className="av num">{r.rank}</span>
                    <span className="row-main">
                      <b>{r.title}</b>
                      <span className="sub">{capitalise(r.domain)}</span>
                    </span>
                    <span className="row-value">
                      <strong className="num">{r.score.toFixed(2)}</strong>
                      <span className="sub">score</span>
                    </span>
                  </a>
                </li>
              ))}
            </ol>
          ) : (
            <p className="muted">None of your skills matched a career yet. Try rewording them.</p>
          )}
        </section>

        <section className="card panel">
          <div className="ph">
            <h2>Saved careers</h2>
            <a href="#/saved">See all</a>
          </div>
          {data.saved.length ? (
            <ul className="list">
              {data.saved.slice(0, 3).map((c) => (
                <li key={c.career_code}>
                  <a className="row" href={`#/careers/${c.career_code}`}>
                    <span className="av"><Icon name="bookmark" size={16} /></span>
                    <span className="row-main">
                      <b>{c.title}</b>
                      <span className="sub">{c.match ? `Your match #${c.match.rank}` : 'Not linked to your skills'}</span>
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small">
              Nothing saved yet. <a href="#/careers">Explore careers</a> and save the ones you want to come back to.
            </p>
          )}
        </section>

        <section className="card panel">
          <div className="ph">
            <h2>Roadmap progress</h2>
            <a href="#/roadmap">Open roadmap</a>
          </div>
          {data.progress.length ? (
            <>
              <p className="num kpi-inline">
                <b>{learningCount}</b> learning · <b>{data.progress.length - learningCount}</b> done
              </p>
              <ul className="chips">
                {data.progress.slice(0, 6).map((p) => (
                  <li key={p.skill_id} className="chip tag">
                    {p.status === 'done' && <Icon name="check" size={13} />}
                    {p.label}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="muted small">Mark skills as learning or done on a career's roadmap to track them here.</p>
          )}
        </section>
      </div>
    </>
  )
}
