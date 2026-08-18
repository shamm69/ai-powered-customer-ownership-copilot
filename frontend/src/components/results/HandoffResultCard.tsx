import { Headphones, Info, TicketCheck } from 'lucide-react'
import type {
  EscalationReason,
  HandoffStatus,
  HumanHandoffResult,
} from '../../types/assistant'

interface HandoffResultCardProps {
  result: HumanHandoffResult
}

const handoffStatusLabels: Record<HandoffStatus, string> = {
  created: 'Created',
}

const escalationReasonLabels: Record<EscalationReason, string> = {
  routed_human_handoff: 'Human support requested',
}

export function HandoffResultCard({ result }: HandoffResultCardProps) {
  return (
    <article aria-label="Demo human handoff result" className="handoff-result-card">
      <header className="handoff-result-card__header">
        <span className="handoff-result-card__icon" aria-hidden="true">
          <Headphones size={22} strokeWidth={1.8} />
        </span>
        <div>
          <span className="handoff-result-card__eyebrow">Human support</span>
          <h3>Demo support handoff created</h3>
        </div>
        <span className="handoff-result-card__demo-label">Demo handoff</span>
      </header>

      <div className="handoff-result-card__reference">
        <TicketCheck size={19} aria-hidden="true" />
        <div>
          <span>Reference ID</span>
          <strong>{result.ticket_id}</strong>
        </div>
      </div>

      <dl className="handoff-result-card__details">
        <div>
          <dt>Status</dt>
          <dd>{handoffStatusLabels[result.status]}</dd>
        </div>
        <div>
          <dt>Reason</dt>
          <dd>{escalationReasonLabels[result.reason]}</dd>
        </div>
        <div className="handoff-result-card__summary">
          <dt>Request summary</dt>
          <dd>{result.request_summary}</dd>
        </div>
      </dl>

      <div className="handoff-result-card__notice">
        <Info size={17} aria-hidden="true" />
        <p>
          This is a local demo handoff. No external CRM, dealer, email, or messaging
          system was contacted.
        </p>
      </div>
    </article>
  )
}
