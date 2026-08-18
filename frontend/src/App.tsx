import { useRef, useState } from 'react'
import './App.css'
import { queryAssistant } from './api/assistant'
import { ApiClientError } from './api/client'
import { AppHeader } from './components/AppHeader'
import { AssistantWorkspace } from './components/AssistantWorkspace'
import { ExperimentalLab } from './components/ExperimentalLab'
import {
  createEmptyPredictiveExperimentDraft,
  parsePredictiveExperimentDraft,
  type PredictiveExperimentDraft,
} from './components/predictiveExperiment'
import { QuickActions } from './components/QuickActions'
import { VehicleOverview } from './components/VehicleOverview'
import type {
  AssistantQueryRequest,
  AssistantQueryResponse,
  PredictiveMaintenanceComparisonResult,
} from './types/assistant'

const predictiveExperimentPrompt =
  'Show the experimental predictive maintenance comparison.'

const demoVehicle = {
  id: 1,
  ownerName: 'Avery Singh',
  manufacturer: 'Aster Motors',
  model: 'Comet',
  modelYear: 2023,
  currentOdometerKm: 12_500,
  serviceIntervalKm: 10_000,
  serviceIntervalMonths: 12,
  latestScheduledServiceDate: '15 Jul 2026',
  latestScheduledServiceOdometerKm: 12_000,
} as const

function App() {
  const [assistantDraft, setAssistantDraft] = useState('')
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null)
  const [assistantResult, setAssistantResult] =
    useState<AssistantQueryResponse | null>(null)
  const [assistantError, setAssistantError] = useState<string | null>(null)
  const [isAssistantLoading, setIsAssistantLoading] = useState(false)
  const [predictiveExperimentDraft, setPredictiveExperimentDraft] =
    useState<PredictiveExperimentDraft | null>(null)
  const [predictiveExperimentResult, setPredictiveExperimentResult] =
    useState<PredictiveMaintenanceComparisonResult | null>(null)
  const [predictiveExperimentError, setPredictiveExperimentError] =
    useState<string | null>(null)
  const [isPredictiveExperimentLoading, setIsPredictiveExperimentLoading] =
    useState(false)
  const assistantInputRef = useRef<HTMLTextAreaElement>(null)
  const requestInFlightRef = useRef(false)
  const experimentRequestInFlightRef = useRef(false)

  function updateAssistantDraft(draft: string) {
    setAssistantDraft(draft)
  }

  function selectAssistantPrompt(prompt: string) {
    updateAssistantDraft(prompt)
    assistantInputRef.current?.focus()
  }

  function openPredictiveExperiment() {
    setPredictiveExperimentDraft(createEmptyPredictiveExperimentDraft())
    setPredictiveExperimentResult(null)
    setPredictiveExperimentError(null)
  }

  function closePredictiveExperiment() {
    setPredictiveExperimentDraft(null)
    setPredictiveExperimentResult(null)
    setPredictiveExperimentError(null)
  }

  function updatePredictiveExperimentField(
    field: keyof PredictiveExperimentDraft,
    value: string,
  ) {
    setPredictiveExperimentDraft((currentDraft) =>
      currentDraft ? { ...currentDraft, [field]: value } : currentDraft,
    )
  }

  async function submitAssistantMessage(message = assistantDraft) {
    const normalizedMessage = message.trim()
    if (!normalizedMessage || requestInFlightRef.current) {
      return
    }

    requestInFlightRef.current = true
    setIsAssistantLoading(true)
    setSubmittedMessage(normalizedMessage)
    setAssistantResult(null)
    setAssistantError(null)
    setAssistantDraft('')

    try {
      const request: AssistantQueryRequest = {
        message: normalizedMessage,
        vehicle_id: demoVehicle.id,
      }
      const result = await queryAssistant(request)
      setAssistantResult(result)
    } catch (error) {
      setAssistantError(getAssistantErrorMessage(error))
    } finally {
      requestInFlightRef.current = false
      setIsAssistantLoading(false)
    }
  }

  async function runPredictiveExperiment() {
    if (!predictiveExperimentDraft || experimentRequestInFlightRef.current) {
      return
    }
    const predictiveInput = parsePredictiveExperimentDraft(predictiveExperimentDraft)
    if (!predictiveInput) {
      return
    }

    experimentRequestInFlightRef.current = true
    setIsPredictiveExperimentLoading(true)
    setPredictiveExperimentResult(null)
    setPredictiveExperimentError(null)

    try {
      const result = await queryAssistant({
        message: predictiveExperimentPrompt,
        predictive_maintenance_input: predictiveInput,
      })
      if (result.invoked_capability !== 'experimental_predictive_maintenance_comparison') {
        setPredictiveExperimentError(
          'The technical preview returned an unexpected response. Please try again.',
        )
        return
      }
      setPredictiveExperimentResult(result.experimental_comparison_result)
    } catch (error) {
      setPredictiveExperimentError(getAssistantErrorMessage(error))
    } finally {
      experimentRequestInFlightRef.current = false
      setIsPredictiveExperimentLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <AppHeader />

      <main className="dashboard">
        <section className="dashboard__intro" id="overview" aria-labelledby="dashboard-title">
          <div>
            <p className="eyebrow">Ownership overview</p>
            <h1 id="dashboard-title">Your ownership overview.</h1>
          </div>
          <p className="dashboard__intro-copy">
            Your Aster Motors Comet, service information, and ownership support in one
            trusted workspace.
          </p>
        </section>

        <div className="dashboard__grid">
          <div className="ownership-column">
            <VehicleOverview vehicle={demoVehicle} />
            <QuickActions
              disabled={isAssistantLoading}
              onSelect={selectAssistantPrompt}
            />
          </div>

          <AssistantWorkspace
            draft={assistantDraft}
            errorMessage={assistantError}
            inputRef={assistantInputRef}
            isLoading={isAssistantLoading}
            onDraftChange={updateAssistantDraft}
            onPromptSelect={selectAssistantPrompt}
            onRetry={() => {
              if (submittedMessage) {
                void submitAssistantMessage(submittedMessage)
              }
            }}
            onSubmit={() => void submitAssistantMessage()}
            response={assistantResult}
            submittedMessage={submittedMessage}
          />
        </div>

        <ExperimentalLab
          draft={predictiveExperimentDraft}
          errorMessage={predictiveExperimentError}
          isLoading={isPredictiveExperimentLoading}
          onChange={updatePredictiveExperimentField}
          onClose={closePredictiveExperiment}
          onOpen={openPredictiveExperiment}
          onRun={() => void runPredictiveExperiment()}
          result={predictiveExperimentResult}
        />
      </main>

      <footer className="app-footer">
        <div className="app-footer__identity">
          <strong>Ownership Copilot</strong>
          <span>Automotive customer-ownership proof of concept</span>
        </div>
        <p>
          Service recommendations use transparent demo rules, not manufacturer
          schedules. Predictive model output is experimental and never replaces the
          scheduled-maintenance status.
        </p>
        <span className="app-footer__demo">Seeded demo workspace</span>
      </footer>
    </div>
  )
}

function getAssistantErrorMessage(error: unknown): string {
  if (!(error instanceof ApiClientError)) {
    return 'Something unexpected happened. Please try your request again.'
  }
  if (error.kind === 'network_error') {
    return 'The assistant could not reach the backend service. Check that it is running and try again.'
  }
  if (error.kind === 'invalid_response') {
    return 'The assistant received an unexpected response. Please try again.'
  }
  if (error.status === 503) {
    return 'That capability is temporarily unavailable. Please try again later.'
  }
  return error.detail
}

export default App
