import {
  CalendarClock,
  CircleAlert,
  CircleCheck,
  Gauge,
  Route,
  TriangleAlert,
} from 'lucide-react'
import type { ComponentType } from 'react'
import type { MaintenanceResult, MaintenanceStatus } from '../../types/assistant'

interface MaintenanceResultCardProps {
  result: MaintenanceResult
}

interface StatusPresentation {
  label: string
  interpretation: string
  tone: 'positive' | 'attention' | 'critical'
  icon: ComponentType<{ 'aria-hidden'?: 'true'; size?: number; strokeWidth?: number }>
}

const statusPresentations: Record<MaintenanceStatus, StatusPresentation> = {
  not_due: {
    label: 'Not Due',
    interpretation:
      'The scheduled-service distance and time limits remain below their due thresholds.',
    tone: 'positive',
    icon: CircleCheck,
  },
  due_soon: {
    label: 'Due Soon',
    interpretation:
      'At least one scheduled-service limit is approaching its due threshold.',
    tone: 'attention',
    icon: TriangleAlert,
  },
  overdue: {
    label: 'Overdue',
    interpretation:
      'At least one scheduled-service interval has reached or exceeded its limit.',
    tone: 'critical',
    icon: CircleAlert,
  },
}

const numberFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 1,
})

function formatKilometres(value: number) {
  return `${numberFormatter.format(value)} km`
}

function formatMonths(value: number) {
  return `${numberFormatter.format(value)} ${Math.abs(value) === 1 ? 'month' : 'months'}`
}

export function MaintenanceResultCard({ result }: MaintenanceResultCardProps) {
  const presentation = statusPresentations[result.status]
  const StatusIcon = presentation.icon

  return (
    <article
      aria-label="Authoritative scheduled maintenance result"
      className={`maintenance-result-card maintenance-result-card--${presentation.tone}`}
    >
      <header className="maintenance-result-card__header">
        <div>
          <span className="maintenance-result-card__eyebrow">
            Scheduled maintenance
          </span>
          <div className="maintenance-result-card__status">
            <span className="maintenance-result-card__status-icon" aria-hidden="true">
              <StatusIcon size={22} strokeWidth={1.9} />
            </span>
            <h3>{presentation.label}</h3>
          </div>
        </div>
        <span className="maintenance-result-card__method">Authoritative status</span>
      </header>

      <p className="maintenance-result-card__interpretation">
        {presentation.interpretation}
      </p>

      <div className="maintenance-result-card__metrics" aria-label="Service metrics">
        <div className="maintenance-metric">
          <Route size={18} aria-hidden="true" />
          <span>Distance travelled</span>
          <strong>{formatKilometres(result.kilometres_travelled_since_last_service)}</strong>
        </div>
        <div className="maintenance-metric">
          <Gauge size={18} aria-hidden="true" />
          <span>Distance remaining</span>
          <strong>{formatKilometres(result.kilometres_remaining)}</strong>
        </div>
        <div className="maintenance-metric">
          <CalendarClock size={18} aria-hidden="true" />
          <span>Time remaining</span>
          <strong>{formatMonths(result.months_remaining)}</strong>
        </div>
      </div>

      <section className="maintenance-result-card__reasons" aria-labelledby="maintenance-reasons">
        <h4 id="maintenance-reasons">Why this status</h4>
        <ul>
          {result.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </section>
    </article>
  )
}
