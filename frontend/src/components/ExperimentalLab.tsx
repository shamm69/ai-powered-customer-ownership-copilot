import { Beaker, ChevronDown, LoaderCircle, Play, ShieldCheck } from 'lucide-react'
import type { PredictiveMaintenanceComparisonResult } from '../types/assistant'
import { PredictiveExperimentPanel } from './PredictiveExperimentPanel'
import {
  parsePredictiveExperimentDraft,
  type PredictiveExperimentDraft,
} from './predictiveExperiment'
import { PredictiveComparisonCard } from './results/PredictiveComparisonCard'

interface ExperimentalLabProps {
  draft: PredictiveExperimentDraft | null
  errorMessage: string | null
  isLoading: boolean
  result: PredictiveMaintenanceComparisonResult | null
  onChange: (field: keyof PredictiveExperimentDraft, value: string) => void
  onClose: () => void
  onOpen: () => void
  onRun: () => void
}

export function ExperimentalLab({
  draft,
  errorMessage,
  isLoading,
  result,
  onChange,
  onClose,
  onOpen,
  onRun,
}: ExperimentalLabProps) {
  const isOpen = draft !== null
  const canRun = draft ? parsePredictiveExperimentDraft(draft) !== null : false

  return (
    <section className="experimental-lab" id="experimental-lab" aria-labelledby="lab-title">
      <div className="experimental-lab__summary">
        <span className="experimental-lab__icon" aria-hidden="true">
          <Beaker size={23} strokeWidth={1.7} />
        </span>
        <div className="experimental-lab__copy">
          <span className="experimental-lab__eyebrow">Technical preview</span>
          <h2 id="lab-title">Experimental model comparison</h2>
          <p>
            Explore the synthetic-data maintenance model separately from the customer
            service experience. The scheduled-maintenance result remains authoritative.
          </p>
        </div>
        <button
          aria-expanded={isOpen}
          className="experimental-lab__toggle"
          disabled={isLoading}
          onClick={isOpen ? onClose : onOpen}
          type="button"
        >
          {isOpen ? 'Close preview' : 'Open model comparison'}
          <ChevronDown aria-hidden="true" size={17} />
        </button>
      </div>

      {!isOpen ? (
        <div className="experimental-lab__boundaries" aria-label="Experiment boundaries">
          <span>Synthetic training data</span>
          <span>Manual demonstration inputs</span>
          <span>No combined maintenance decision</span>
        </div>
      ) : null}

      {draft ? (
        <div className="experimental-lab__workspace">
          <div className="experimental-lab__form">
            <div className="experimental-lab__context">
              <ShieldCheck size={18} aria-hidden="true" />
              <p>
                In a production integration, these values would normally come from
                stored vehicle, service, and usage systems—not manual customer entry.
              </p>
            </div>
            <PredictiveExperimentPanel
              disabled={isLoading}
              draft={draft}
              onChange={onChange}
            />
            <button
              className="experimental-lab__run"
              disabled={!canRun || isLoading}
              onClick={onRun}
              type="button"
            >
              {isLoading ? (
                <LoaderCircle className="spinning" size={18} aria-hidden="true" />
              ) : (
                <Play size={17} aria-hidden="true" />
              )}
              {isLoading ? 'Running comparison…' : 'Run experimental comparison'}
            </button>
            {errorMessage ? (
              <div className="experimental-lab__error" role="alert">
                <strong>Technical preview unavailable</strong>
                <p>{errorMessage}</p>
              </div>
            ) : null}
          </div>

          {result ? (
            <div className="experimental-lab__result">
              <PredictiveComparisonCard result={result} />
            </div>
          ) : (
            <div className="experimental-lab__empty">
              <Beaker size={24} aria-hidden="true" />
              <strong>Comparison output will appear here</strong>
              <p>Complete all eight demonstration inputs, then run the experiment.</p>
            </div>
          )}
        </div>
      ) : null}
    </section>
  )
}
