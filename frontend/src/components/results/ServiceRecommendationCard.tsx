import { CalendarCheck, CheckCircle2, Wrench } from 'lucide-react'
import type {
  MaintenanceStatus,
  RecommendationPriority,
  ServiceRecommendationResult,
  ServiceType,
} from '../../types/assistant'

interface ServiceRecommendationCardProps {
  result: ServiceRecommendationResult
}

const serviceLabels: Record<ServiceType, string> = {
  periodic_maintenance_service: 'Periodic Maintenance Service',
  pre_trip_inspection: 'Pre-Trip Inspection',
  tyre_inspection_rotation: 'Tyre Inspection / Rotation',
  battery_health_check: 'Battery Health Check',
  no_service_required: 'No Service Required',
}

const priorityLabels: Record<RecommendationPriority, string> = {
  none: 'No action needed',
  routine: 'Routine',
  recommended: 'Recommended',
  due_soon: 'Due soon',
  urgent: 'Urgent',
}

const maintenanceLabels: Record<MaintenanceStatus, string> = {
  not_due: 'Not Due',
  due_soon: 'Due Soon',
  overdue: 'Overdue',
}

export function ServiceRecommendationCard({
  result,
}: ServiceRecommendationCardProps) {
  return (
    <article
      aria-label="Deterministic service recommendations"
      className="recommendation-result-card"
    >
      <header className="recommendation-result-card__header">
        <span className="recommendation-result-card__icon" aria-hidden="true">
          <Wrench size={21} strokeWidth={1.8} />
        </span>
        <div>
          <span className="recommendation-result-card__eyebrow">
            Recommended next service
          </span>
          <h3>Deterministic service guidance</h3>
        </div>
        <span className="recommendation-result-card__method">Demo MVP rules</span>
      </header>

      <div className="recommendation-result-card__authority">
        <CalendarCheck size={18} aria-hidden="true" />
        <span>Authoritative scheduled status</span>
        <strong>{maintenanceLabels[result.authoritative_maintenance.status]}</strong>
      </div>

      <ol className="recommendation-result-card__list">
        {result.recommendations.map((recommendation) => (
          <li key={recommendation.service_type}>
            <div className="recommendation-result-card__item-heading">
              <div>
                <CheckCircle2 size={18} aria-hidden="true" />
                <h4>{serviceLabels[recommendation.service_type]}</h4>
              </div>
              <span data-priority={recommendation.priority}>
                {priorityLabels[recommendation.priority]}
              </span>
            </div>
            <p>{recommendation.reason}</p>
            <ul aria-label={`Supporting context for ${serviceLabels[recommendation.service_type]}`}>
              {recommendation.supporting_factors.map((factor) => (
                <li key={factor}>{factor}</li>
              ))}
            </ul>
          </li>
        ))}
      </ol>

      <p className="recommendation-result-card__note">
        Service suggestions use explainable demo rules and do not diagnose a
        mechanical fault or replace the authoritative maintenance status.
      </p>
    </article>
  )
}
