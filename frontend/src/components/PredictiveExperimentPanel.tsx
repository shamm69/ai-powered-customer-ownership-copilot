import { Beaker } from 'lucide-react'
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
}

export function PredictiveExperimentPanel({
  disabled,
  draft,
  onChange,
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
          <span>Manual demonstration inputs</span>
          <h3 id="predictive-experiment-title">Model input set</h3>
        </div>
      </header>

      <p className="predictive-experiment-panel__description">
        Enter all eight values used by the controlled synthetic-data experiment. They
        are not live vehicle telemetry and do not affect scheduled maintenance.
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
