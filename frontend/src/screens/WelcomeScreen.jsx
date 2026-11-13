import { PageHeader } from '../components.jsx'
import { displayName } from '../format.js'
import { Icon } from '../icons.jsx'

const STEPS = [
  {
    icon: 'plus',
    title: 'Tell us what you can do',
    text: 'List your skills in your own words: tools, topics or things you do well. Three or more give better results.',
  },
  {
    icon: 'matches',
    title: 'See the careers that fit',
    text: 'AjiraGuide ranks the tech careers that use your skills and explains each match in plain words.',
  },
  {
    icon: 'roadmap',
    title: 'Plan what to learn next',
    text: 'Each career lists the skills you still need, most important first. Track them as you learn.',
  },
]

// Shown once, straight after an account is created.
export default function WelcomeScreen({ user }) {
  return (
    <>
      <PageHeader title={`Welcome, ${displayName(user)}`} subtitle="AjiraGuide suggests tech careers from the skills you already have. It takes three steps." />
      <section className="card panel" aria-labelledby="steps-heading">
        <div className="ph"><h2 id="steps-heading">How it works</h2></div>
        <ol className="list">
          {STEPS.map((step, i) => (
            <li key={step.title} className="row">
              <span className="av"><Icon name={step.icon} size={16} /></span>
              <span className="row-main">
                <b>{i + 1}. {step.title}</b>
                <span className="sub">{step.text}</span>
              </span>
            </li>
          ))}
        </ol>
        <div className="actions">
          <a className="btn primary" href="#/profile">Add your skills</a>
          <a className="btn glass" href="#/careers">Look around first</a>
        </div>
      </section>
    </>
  )
}
