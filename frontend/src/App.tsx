import { useRef, useState } from 'react'
import './App.css'
import { queryAssistant } from './api/assistant'
import { ApiClientError } from './api/client'
import { AppHeader } from './components/AppHeader'
import { AssistantWorkspace } from './components/AssistantWorkspace'
import {
  createEmptyPredictiveExperimentDraft,
  parsePredictiveExperimentDraft,
  type PredictiveExperimentDraft,
} from './components/predictiveExperiment'
import { QuickActions } from './components/QuickActions'
import { VehicleOverview } from './components/VehicleOverview'
import type { AssistantQueryRequest, AssistantQueryResponse } from './types/assistant'

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
  const assistantInputRef = useRef<HTMLTextAreaElement>(null)
  const requestInFlightRef = useRef(false)

  function updateAssistantDraft(draft: string) {
    setAssistantDraft(draft)
  }

  function selectAssistantPrompt(prompt: string) {
    setPredictiveExperimentDraft(null)
    updateAssistantDraft(prompt)
    assistantInputRef.current?.focus()
  }

  function openPredictiveExperiment() {
    setPredictiveExperimentDraft(createEmptyPredictiveExperimentDraft())
    updateAssistantDraft(predictiveExperimentPrompt)
  }

  function closePredictiveExperiment() {
    setPredictiveExperimentDraft(null)
    if (assistantDraft === predictiveExperimentPrompt) {
      updateAssistantDraft('')
    }
    assistantInputRef.current?.focus()
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

    const predictiveInput = predictiveExperimentDraft
      ? parsePredictiveExperimentDraft(predictiveExperimentDraft)
      : null
    if (predictiveExperimentDraft && !predictiveInput) {
      return
    }

    requestInFlightRef.current = true
    setIsAssistantLoading(true)
    setSubmittedMessage(normalizedMessage)
    setAssistantResult(null)
    setAssistantError(null)
    setAssistantDraft('')

    try {
      const request: AssistantQueryRequest = predictiveInput
        ? { message: normalizedMessage, predictive_maintenance_input: predictiveInput }
        : { message: normalizedMessage, vehicle_id: demoVehicle.id }
      const result = await queryAssistant(request)
      setAssistantResult(result)
      setPredictiveExperimentDraft(null)
    } catch (error) {
      setAssistantError(getAssistantErrorMessage(error))
    } finally {
      requestInFlightRef.current = false
      setIsAssistantLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <AppHeader />

      <main className="dashboard">
        <section className="dashboard__intro" aria-labelledby="dashboard-title">
          <div>
            <p className="eyebrow">Avery&apos;s garage</p>
            <h1 id="dashboard-title">Your vehicle, clearly understood.</h1>
          </div>
          <p className="dashboard__intro-copy">
            Review the essentials, check maintenance, or ask for grounded ownership support.
          </p>
        </section>

        <div className="dashboard__grid">
          <div className="ownership-column">
            <VehicleOverview vehicle={demoVehicle} />
            <QuickActions
              disabled={isAssistantLoading}
              onSelect={selectAssistantPrompt}
              onSelectExperiment={openPredictiveExperiment}
            />
          </div>

          <AssistantWorkspace
            draft={assistantDraft}
            errorMessage={assistantError}
            inputRef={assistantInputRef}
            isLoading={isAssistantLoading}
            onDraftChange={updateAssistantDraft}
            onPromptSelect={selectAssistantPrompt}
            onPredictiveExperimentDismiss={closePredictiveExperiment}
            onPredictiveExperimentFieldChange={updatePredictiveExperimentField}
            onRetry={() => {
              if (submittedMessage) {
                void submitAssistantMessage(submittedMessage)
              }
            }}
            onSubmit={() => void submitAssistantMessage()}
            response={assistantResult}
            submittedMessage={submittedMessage}
            predictiveExperimentDraft={predictiveExperimentDraft}
          />
        </div>
      </main>

      <footer className="app-footer">
        <span>Ownership Copilot</span>
        <span>Demo experience · Synthetic vehicle data</span>
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
