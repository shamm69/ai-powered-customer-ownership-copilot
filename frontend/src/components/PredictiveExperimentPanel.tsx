import { Beaker, X } from 'lucide-react'
import {
  predictiveFields,
  validatePredictiveExperimentDraft,
  type PredictiveExperimentDraft,
  type PredictiveField,
} from './predictiveExperiment'

interface PredictiveExperimentPanelProps {
  disabled: boolean
  draft: PredictiveExperimentDraft
  onChange: (field: PredictiveField, value: string) => void
  onDismiss: () => void
}

export function PredictiveExperimentPanel({
  disabled,
  draft,
  onChange,
  onDismiss,
}: PredictiveExperimentPanelProps) {
  const errors = validatePredictiveExperimentDraft(draft)
  const completedFieldCount = predictiveFields.filter(
    (field) => draft[field.key].trim() && !errors[field.key],
  ).length

  return (
    <section
      aria-labelledby="predictive-experiment-title"
      className="predictive-experiment-panel"
    >
      <header className="predictive-experiment-panel__header">
        <span className="predictive-experiment-panel__icon" aria-hidden="true">
          <Beaker size={20} strokeWidth={1.8} />
        </span>
        <div>
          <span>Experimental · Synthetic inputs</span>
          <h3 id="predictive-experiment-title">Predictive-maintenance experiment</h3>
        </div>
        <button
          aria-label="Close predictive experiment"
          disabled={disabled}
          onClick={onDismiss}
          type="button"
        >
          <X size={18} aria-hidden="true" />
        </button>
      </header>

      <p className="predictive-experiment-panel__description">
        Enter all eight synthetic demo inputs. They are not live connected-vehicle
        telemetry, and the experiment does not override scheduled maintenance.
      </p>

      <div className="predictive-experiment-panel__fields">
        {predictiveFields.map((field, index) => {
          const error = draft[field.key] ? errors[field.key] : undefined
          const errorId = `${field.key}-error`
          return (
            <label key={field.key}>
              <span>{field.label}</span>
              <input
                aria-describedby={error ? errorId : undefined}
                aria-invalid={Boolean(error)}
                autoFocus={index === 0}
                disabled={disabled}
                max={field.max}
                min={field.min}
                name={field.key}
                onChange={(event) => onChange(field.key, event.target.value)}
                required
                step="any"
                type="number"
                value={draft[field.key]}
              />
              {error ? (
                <small className="predictive-experiment-panel__field-error" id={errorId}>
                  {error}
                </small>
              ) : null}
            </label>
          )
        })}
      </div>

      <div className="predictive-experiment-panel__footer">
        <span>{completedFieldCount} of 8 valid fields</span>
        <span>Complete every field to enable submission</span>
      </div>
    </section>
  )
}
