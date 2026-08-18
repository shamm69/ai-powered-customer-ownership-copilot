import {
  CircleHelp,
  FlaskConical,
  Headphones,
  Route,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react'

interface QuickAction {
  label: string
  description: string
  prompt: string
  icon: LucideIcon
  experimental?: boolean
}

interface QuickActionsProps {
  disabled?: boolean
  onSelect: (prompt: string) => void
  onSelectExperiment: () => void
}

const quickActions: QuickAction[] = [
  {
    label: 'Check service status',
    description: 'Review scheduled maintenance',
    prompt: 'Is my vehicle due for service?',
    icon: ShieldCheck,
  },
  {
    label: 'Explain a warning light',
    description: 'Find grounded support guidance',
    prompt: 'What does a warning light mean?',
    icon: CircleHelp,
  },
  {
    label: 'Prepare for a long trip',
    description: 'See practical vehicle checks',
    prompt: 'What should I check before a long trip?',
    icon: Route,
  },
  {
    label: 'Talk to human support',
    description: 'Create a demo handoff request',
    prompt: 'I want to speak to a human agent.',
    icon: Headphones,
  },
  {
    label: 'Explore predictive experiment',
    description: 'Compare rule and model signals with synthetic inputs',
    prompt: 'Show the experimental predictive maintenance comparison.',
    icon: FlaskConical,
    experimental: true,
  },
]

export function QuickActions({
  disabled = false,
  onSelect,
  onSelectExperiment,
}: QuickActionsProps) {
  return (
    <section className="quick-actions" aria-labelledby="quick-actions-title">
      <div className="section-heading">
        <div>
          <p className="section-label">Shortcuts</p>
          <h2 id="quick-actions-title">Quick actions</h2>
        </div>
        <span>Choose a starting point</span>
      </div>

      <div className="quick-actions__grid">
        {quickActions.map(({ label, description, prompt, icon: Icon, experimental }) => (
          <button
            className={`quick-action${experimental ? ' quick-action--experimental' : ''}`}
            disabled={disabled}
            key={label}
            onClick={() => (experimental ? onSelectExperiment() : onSelect(prompt))}
            type="button"
          >
            <span className="quick-action__icon" aria-hidden="true">
              <Icon size={19} strokeWidth={1.8} />
            </span>
            <span>
              <span className="quick-action__title">
                <strong>{label}</strong>
                {experimental ? <em>Experimental</em> : null}
              </span>
              <small>{description}</small>
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
