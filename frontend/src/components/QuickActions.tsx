import {
  CircleHelp,
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
}

interface QuickActionsProps {
  disabled?: boolean
  onSelect: (prompt: string) => void
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
    prompt: 'I want to speak with support.',
    icon: Headphones,
  },
]

export function QuickActions({ disabled = false, onSelect }: QuickActionsProps) {
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
        {quickActions.map(({ label, description, prompt, icon: Icon }) => (
          <button
            className="quick-action"
            disabled={disabled}
            key={label}
            onClick={() => onSelect(prompt)}
            type="button"
          >
            <span className="quick-action__icon" aria-hidden="true">
              <Icon size={19} strokeWidth={1.8} />
            </span>
            <span>
              <strong>{label}</strong>
              <small>{description}</small>
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
