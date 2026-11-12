import { useEffect, useState } from 'react'

import { getCareer, getRecommendation } from '../api.js'
import CareerGraph from '../CareerGraph.jsx'
import { Disclosure, Meter, Notice, PageHeader, Pill, SaveButton, Status } from '../components.jsx'
import { capitalise, fitLabel, sourceNames } from '../format.js'
import { Icon } from '../icons.jsx'

// The skills to develop shown before "show more"; the rest keep their order.
const NEXT_STEPS = 3
const TECHNICAL_ID = 'how-calculated'

export default function CareerDetailScreen({ code }) {
  const [profile, setProfile] = useState(null)
  const [career, setCareer] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    // App keys this screen by career code, so state starts fresh for each career.
    let current = true
    getCareer(code)
      .then(async (result) => {
        // Only a career linked to the user's skills has an explained match.
        const match = result.match ? await getRecommendation(code) : null
        if (!current) return
        setProfile(result)
        setCareer(match)
      })
      .catch((err) => current && setError(err.message))
    return () => {
      current = false
    }
  }, [code])

  const back = profile?.match
    ? { href: '#/recommendations', label: 'All my matches' }
    : { href: '#/careers', label: 'Explore careers' }

  if (!profile) {
    return (
      <>
        <PageHeader title="Career" back={back} />
        <Status loading={!error} error={error} />
      </>
    )
  }

  const subtitle = career
    ? `Match #${career.rank} · ${capitalise(profile.domain)}`
    : `${capitalise(profile.domain)} · not linked to your skills yet`

  return (
    <>
      <PageHeader title={profile.title} subtitle={subtitle} back={back} />

      <div className="button-row">
        <SaveButton code={code} saved={profile.saved} />
        {career && (
          <>
            <a className="btn glass" href={`#/roadmap/${code}`}><Icon name="roadmap" />Skills roadmap</a>
            <button type="button" className="btn glass" onClick={openTechnical}>
              <Icon name="graph" />How this was calculated
            </button>
          </>
        )}
      </div>

      {career ? <MatchDetail career={career} description={profile.description} /> : <Requirements profile={profile} />}
    </>
  )
}

function openTechnical() {
  const details = document.getElementById(TECHNICAL_ID)
  details.open = true
  details.scrollIntoView()
  details.querySelector('summary').focus()
}

export function MatchDetail({ career, description }) {
  return (
    <>
      <section className="hero-card" aria-labelledby="match-heading">
        <h2 className="mono" id="match-heading"><i aria-hidden="true" />Why it suits you</h2>
        <p className="hero-figure">{fitLabel(career.fit)}</p>
        <p className="hero-sub num">Match score {career.score.toFixed(2)} on a 0 to 1 scale · #{career.rank} of your matches</p>
        <p className="hero-reason">{career.reason}</p>
      </section>

      <div className="split-2">
        <SkillsYouHave skills={career.skill_contributions} />
        <SkillsToDevelop gap={career.skills_gap} code={career.career_code} />
      </div>

      <section className="card panel" aria-labelledby="about-heading">
        <h2 id="about-heading">About this career</h2>
        <p className="explanation-lead">{description}</p>
      </section>

      <TechnicalExplanation career={career} />
    </>
  )
}

function SkillsYouHave({ skills }) {
  return (
    <section className="card panel" aria-labelledby="have-heading">
      <div className="ph">
        <h2 id="have-heading">Skills you already have</h2>
        <span className="num">{skills.length}</span>
      </div>
      {skills.length ? (
        <ul className="list">
          {skills.map((s) => (
            <li key={s.skill_id} className="row">
              <span className={s.low_confidence ? 'av unsure' : 'av have'}>
                <Icon name={s.low_confidence ? 'alert' : 'check'} size={16} />
              </span>
              <span className="row-main">
                <b>{s.skill_label}</b>
                {s.low_confidence ? (
                  <span className="sub">Unsure match for your “{s.query}”. <a href="#/assessment">Reword it</a></span>
                ) : (
                  s.query.toLowerCase() !== s.skill_label.toLowerCase() && <span className="sub">You said “{s.query}”</span>
                )}
              </span>
              <span className="row-value">
                <Pill>{s.requirement}</Pill>
                {s.low_confidence && <Pill tone="warn">Unsure match</Pill>}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">This career does not directly require any of your listed skills.</p>
      )}
    </section>
  )
}

function GapRow({ skill, position }) {
  return (
    <li className="row">
      <span className="av num"><span className="visually-hidden">Priority </span>{position}</span>
      <span className="row-main">
        <b>{skill.label}</b>
        <span className="sub">{capitalise(skill.skill_type)}</span>
      </span>
      <span className="row-value"><Pill>{skill.requirement}</Pill></span>
    </li>
  )
}

function SkillsToDevelop({ gap, code }) {
  const first = gap.slice(0, NEXT_STEPS)
  const rest = gap.slice(NEXT_STEPS)
  return (
    <section className="card panel" aria-labelledby="develop-heading">
      <div className="ph">
        <h2 id="develop-heading">Skills to develop</h2>
        <span className="num">Top {gap.length}</span>
      </div>
      {gap.length ? (
        <>
          <p className="muted small">
            Start with these. They are what the career needs most, and more specific to it than skills most careers share.
          </p>
          <ol className="list">
            {first.map((g, i) => <GapRow key={g.skill_id} skill={g} position={i + 1} />)}
          </ol>
          {rest.length > 0 && (
            <Disclosure summary={`Show ${rest.length} more`} className="more">
              <ol className="list" start={NEXT_STEPS + 1}>
                {rest.map((g, i) => <GapRow key={g.skill_id} skill={g} position={NEXT_STEPS + i + 1} />)}
              </ol>
            </Disclosure>
          )}
          <p className="panel-foot"><a href={`#/roadmap/${code}`}>Track these in your roadmap <Icon name="forward" size={14} /></a></p>
        </>
      ) : (
        <p className="empty">Your skills already include every skill this career requires.</p>
      )}
    </section>
  )
}

// Everything the score is computed from, unchanged from the engine: the full
// explanation, the three components and their weights, the graph and the
// data source of every skill to develop.
function TechnicalExplanation({ career }) {
  const c = career.components
  const w = career.weights
  return (
    <section className="card panel">
      <Disclosure summary="How this match was calculated" id={TECHNICAL_ID} className="technical">
        <h3>What the match score means</h3>
        <p>
          The match score runs from 0 to 1 and ranks careers against each other for the skills you listed. It is not a
          percentage, a measure of how qualified you are, or a prediction of success in the career.
        </p>
        <p>
          It measures how well your skills fit the career, not how many of its requirements you meet, so a strong match
          can still leave skills to develop. Scores change when you edit your skills, so compare careers within one list
          rather than over time.
        </p>

        <h3>Full explanation</h3>
        <div className="explanation">
          {career.explanation.map((sentence) => <p key={sentence}>{sentence}</p>)}
        </div>

        <h3>Score breakdown</h3>
        {w.background == null ? (
          <p className="formula num">
            score = {w.coverage.toFixed(2)} × coverage + {w.profile_similarity.toFixed(2)} × similarity
            {' '}+ {w.graph_proximity.toFixed(2)} × proximity = {career.score.toFixed(2)}
          </p>
        ) : (
          <p className="formula num">
            score = {(1 - w.background).toFixed(2)} × ({w.coverage.toFixed(2)} × coverage + {w.profile_similarity.toFixed(2)} × similarity
            {' '}+ {w.graph_proximity.toFixed(2)} × proximity) + {w.background.toFixed(2)} × background = {career.score.toFixed(2)}
          </p>
        )}
        <div className="meters stacked">
          <Meter label="Coverage: the share of your listed skills this career uses" value={c.coverage} weight={w.coverage} />
          <Meter label="Similarity: how closely your skills match the O*NET description of the role" value={c.profile_similarity} weight={w.profile_similarity} />
          <Meter label="Proximity: closeness in the skills graph, where the closest career scores 1.00" value={c.graph_proximity} weight={w.graph_proximity} />
          {w.background != null && (
            <Meter label="Background: how closely your interests, studies and experience match the role's description" value={c.background_similarity} weight={w.background} />
          )}
        </div>

        <h3>Skills graph</h3>
        <CareerGraph career={career} />

        <h3>How your skills were matched</h3>
        <ul className="list">
          {career.skill_contributions.map((s) => (
            <li key={s.skill_id} className="row evidence">
              <span className="row-main">
                <b>“{s.query}” → {s.skill_label}</b>
                <span className="sub num">
                  Match similarity {s.match_similarity.toFixed(2)}{s.low_confidence && ' (below the confidence threshold)'}
                  {' '}· requirement weight {s.edge_weight.toFixed(2)} · share of coverage {s.coverage_share.toFixed(2)}
                </span>
              </span>
            </li>
          ))}
        </ul>

        <h3>Where the skills to develop come from</h3>
        <p className="muted small">Ordered by requirement weight squared times how specific the skill is to this career (IDF).</p>
        <ol className="list">
          {career.skills_gap.map((g) => (
            <li key={g.skill_id} className="row evidence">
              <span className="row-main">
                <b>{g.label}</b>
                <span className="sub num">
                  {sourceNames(g.sources)} · requirement weight {g.edge_weight.toFixed(2)} · IDF {g.idf.toFixed(2)}
                </span>
              </span>
            </li>
          ))}
        </ol>
      </Disclosure>
    </section>
  )
}

// For a career none of the user's skills link to: what it asks for, from the knowledge graph.
function Requirements({ profile }) {
  return (
    <>
      <section className="card panel" aria-labelledby="about-heading">
        <h2 id="about-heading">About this career</h2>
        <p className="explanation-lead">{profile.description}</p>
      </section>

      <Notice icon="bulb" title="None of your skills link to this career yet" action={{ href: '#/assessment', label: 'Edit skills' }}>
        Add skills from the list below that you already have, and it will be ranked and explained for you.
      </Notice>

      <div className="split-2">
        <section className="card panel">
          <div className="ph">
            <h2>What this career requires</h2>
            <span className="num">{profile.skill_count}</span>
          </div>
          <p className="muted small">The most important first; skills distinctive to this career lead.</p>
          <ol className="list">
            {profile.requirements.map((r, i) => (
              <li key={r.skill_id} className="row">
                <span className="av num">{i + 1}</span>
                <span className="row-main">
                  <b>{r.label}</b>
                  <span className="sub">{capitalise(r.skill_type || 'skill')}</span>
                </span>
                <span className="row-value"><Pill>{r.requirement}</Pill></span>
              </li>
            ))}
          </ol>
        </section>

        <section className="card panel">
          <div className="ph">
            <h2>Tools used</h2>
            <span className="num">{profile.tool_count}</span>
          </div>
          <p className="muted small">The software this career relies on most.</p>
          <ul className="chips">
            {profile.tools.map((t) => (
              <li key={t.skill_id} className="chip tag">{t.label}</li>
            ))}
          </ul>
        </section>
      </div>
    </>
  )
}
