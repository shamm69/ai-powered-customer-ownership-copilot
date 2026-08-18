import { Beaker, Info, Split } from 'lucide-react'
import type {
  BinarySignal,
  MaintenanceSignalRelationship,
  PredictiveMaintenanceComparisonResult,
} from '../../types/assistant'
import { MaintenanceResultCard } from './MaintenanceResultCard'

interface PredictiveComparisonCardProps {
  result: PredictiveMaintenanceComparisonResult
}

const relationshipLabels: Record<MaintenanceSignalRelationship, string> = {
  agree_negative: 'Both signals indicate no near-term maintenance flag',
  agree_positive: 'Both signals indicate a maintenance flag',
  deterministic_only_positive: 'Scheduled rules flag maintenance; the model does not',
  ml_only_positive: 'The model flags maintenance; scheduled rules do not',
}

const percentFormatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  maximumFractionDigits: 1,
})

function signalLabel(signal: BinarySignal) {
  return signal === 1 ? 'Flagged (1)' : 'Not flagged (0)'
}

export function PredictiveComparisonCard({ result }: PredictiveComparisonCardProps) {
  return (
    <section
      aria-label="Experimental predictive maintenance comparison"
      className="predictive-comparison-card"
    >
      <header className="predictive-comparison-card__header">
        <span className="predictive-comparison-card__icon" aria-hidden="true">
          <Beaker size={22} strokeWidth={1.8} />
        </span>
        <div>
          <span className="predictive-comparison-card__eyebrow">Technical preview</span>
          <h3>Experimental model comparison</h3>
        </div>
        <span
          aria-label="Experimental model output"
          className="predictive-comparison-card__badge"
        >
          Experimental
        </span>
      </header>

      <p className="predictive-comparison-card__intro">
        A side-by-side technical comparison of scheduled-maintenance rules and a model
        trained on synthetic data. It does not produce a combined customer decision.
      </p>

      <section
        aria-labelledby="authoritative-maintenance-heading"
        className="predictive-comparison-card__section"
      >
        <div className="predictive-comparison-card__section-heading">
          <div>
            <span>Authoritative</span>
            <h4 id="authoritative-maintenance-heading">Scheduled maintenance</h4>
          </div>
          <small>Deterministic rules</small>
        </div>
        <MaintenanceResultCard result={result.deterministic} />
      </section>

      <section
        aria-labelledby="experimental-signal-heading"
        className="predictive-comparison-card__section predictive-comparison-card__section--experimental"
      >
        <div className="predictive-comparison-card__section-heading">
          <div>
            <span>Experimental</span>
            <h4 id="experimental-signal-heading">90-day ML signal</h4>
          </div>
          <small>Model artifact v{result.experimental_ml.artifact_schema_version}</small>
        </div>

        <div className="predictive-comparison-card__metrics">
          <div>
            <span>90-day model flag</span>
            <strong>
              {signalLabel(
                result.experimental_ml.maintenance_needed_within_90_days_prediction,
              )}
            </strong>
          </div>
          <div>
            <span>Model probability</span>
            <strong>
              {percentFormatter.format(result.experimental_ml.positive_class_probability)}
            </strong>
          </div>
          <div>
            <span>Stored threshold</span>
            <strong>{percentFormatter.format(result.experimental_ml.threshold)}</strong>
          </div>
        </div>

        <div className="predictive-comparison-card__relationship">
          <Split size={18} aria-hidden="true" />
          <div>
            <span>Signal relationship</span>
            <strong>{relationshipLabels[result.comparison.relationship]}</strong>
            <small>
              Deterministic signal {result.comparison.deterministic_binary_signal} · ML
              signal {result.comparison.experimental_ml_binary_signal}
            </small>
          </div>
        </div>
      </section>

      <div className="predictive-comparison-card__notice">
        <Info size={18} aria-hidden="true" />
        <p>
          This synthetic-data model did not meet the predefined replacement/useful-value
          gate. Its output is shown for comparison only and does not override the
          authoritative deterministic service status.
        </p>
      </div>
    </section>
  )
}
