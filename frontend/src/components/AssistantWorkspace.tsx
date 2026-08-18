import {
  ArrowUp,
  BookOpenText,
  CircleAlert,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import { useEffect, useRef, type KeyboardEvent, type RefObject } from 'react'
import type {
  AssistantQueryResponse,
  OrchestrationOutcome,
} from '../types/assistant'
import { HandoffResultCard } from './results/HandoffResultCard'
import { MaintenanceResultCard } from './results/MaintenanceResultCard'
import { PredictiveComparisonCard } from './results/PredictiveComparisonCard'
import { ServiceRecommendationCard } from './results/ServiceRecommendationCard'
import { SupportResultCard } from './results/SupportResultCard'

interface AssistantWorkspaceProps {
  draft: string
  submittedMessage: string | null
  response: AssistantQueryResponse | null
  errorMessage: string | null
  isLoading: boolean
  inputRef: RefObject<HTMLTextAreaElement | null>
  onDraftChange: (draft: string) => void
  onPromptSelect: (prompt: string) => void
  onSubmit: () => void
  onRetry: () => void
}

const suggestedQuestions = [
  'Is my vehicle due for service?',
  'What service should I get for my vehicle?',
  'What does a warning light mean?',
]

const outcomeLabels: Record<OrchestrationOutcome, string> = {
  executed: 'Completed',
  context_required: 'More information needed',
  not_yet_integrated: 'Not available yet',
  unsupported: 'Outside available support',
  clarification_required: 'Clarification needed',
}

export function AssistantWorkspace({
  draft,
  submittedMessage,
  response,
  errorMessage,
  isLoading,
  inputRef,
  onDraftChange,
  onPromptSelect,
  onSubmit,
  onRetry,
}: AssistantWorkspaceProps) {
  const canSubmit = draft.trim().length > 0 && !isLoading

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (canSubmit) {
        onSubmit()
      }
    }
  }

  return (
    <section className="assistant-panel" id="assistant" aria-labelledby="assistant-title">
      <div className="assistant-panel__topline">
        <span className="assistant-identity" id="assistant-title">
          <span className="assistant-identity__icon" aria-hidden="true">
            <Sparkles size={18} strokeWidth={1.8} />
          </span>
          Ownership assistant
        </span>
        <span className="grounding-note">
          <BookOpenText size={15} aria-hidden="true" />
          Grounded support
        </span>
      </div>

      {submittedMessage ? (
        <AssistantExchange
          errorMessage={errorMessage}
          isLoading={isLoading}
          onRetry={onRetry}
          response={response}
          submittedMessage={submittedMessage}
        />
      ) : (
        <AssistantWelcome />
      )}

      <div className="suggested-prompts" aria-label="Suggested questions">
        {suggestedQuestions.map((question) => (
          <button
            disabled={isLoading}
            key={question}
            onClick={() => onPromptSelect(question)}
            type="button"
          >
            {question}
          </button>
        ))}
      </div>

      <form
        aria-label="Assistant question form"
        className="assistant-composer"
        onSubmit={(event) => {
          event.preventDefault()
          if (canSubmit) {
            onSubmit()
          }
        }}
      >
        <label className="visually-hidden" htmlFor="assistant-question">
          Ask the ownership assistant
        </label>
        <textarea
          disabled={isLoading}
          id="assistant-question"
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about maintenance, service recommendations, or vehicle support…"
          ref={inputRef}
          rows={3}
          value={draft}
        />
        <button
          aria-label={isLoading ? 'Request in progress' : 'Send question'}
          className="send-button"
          disabled={!canSubmit}
          type="submit"
        >
          {isLoading ? (
            <LoaderCircle className="spinning" size={20} aria-hidden="true" />
          ) : (
            <ArrowUp size={20} aria-hidden="true" />
          )}
        </button>
      </form>

      <div className="assistant-panel__footer">
        <span>Enter to send · Shift + Enter for a new line</span>
        <span>Selected vehicle context included</span>
      </div>
    </section>
  )
}

function AssistantWelcome() {
  return (
    <div className="assistant-panel__welcome">
      <div className="assistant-symbol" aria-hidden="true">
        <MessageSquareText size={28} strokeWidth={1.5} />
      </div>
      <p className="section-label">Here for the road ahead</p>
      <h2>How can I help with your vehicle today?</h2>
      <p>
        Check scheduled maintenance, understand what service to consider next, search
        the support guide, or ask for human help.
      </p>
      <ul className="assistant-capabilities" aria-label="Available ownership help">
        <li>Maintenance status</li>
        <li>Service recommendations</li>
        <li>Warning-light guidance</li>
        <li>Human help</li>
      </ul>
    </div>
  )
}

interface AssistantExchangeProps {
  submittedMessage: string
  response: AssistantQueryResponse | null
  errorMessage: string | null
  isLoading: boolean
  onRetry: () => void
}

function AssistantExchange({
  submittedMessage,
  response,
  errorMessage,
  isLoading,
  onRetry,
}: AssistantExchangeProps) {
  const responseRef = useRef<HTMLDivElement>(null)
  const loadingPresentation = getLoadingPresentation(submittedMessage)

  useEffect(() => {
    if (isLoading || (!response && !errorMessage)) {
      return
    }
    const prefersReducedMotion =
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    responseRef.current?.scrollIntoView?.({
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
      block: 'nearest',
    })
    responseRef.current?.focus({ preventScroll: true })
  }, [errorMessage, isLoading, response])

  return (
    <div className="assistant-exchange" aria-live="polite">
      <div className="user-request">
        <span>You asked</span>
        <p>{submittedMessage}</p>
      </div>

      <div
        aria-label="Assistant result"
        className="assistant-response"
        ref={responseRef}
        tabIndex={-1}
      >
        {isLoading ? (
          <div className="assistant-loading" role="status">
            <LoaderCircle className="spinning" size={22} aria-hidden="true" />
            <div>
              <strong>{loadingPresentation.title}</strong>
              <span>{loadingPresentation.detail}</span>
              <div className="assistant-loading__skeleton" aria-hidden="true">
                <i />
                <i />
              </div>
            </div>
          </div>
        ) : null}

        {errorMessage ? (
          <div className="assistant-error" role="alert">
            <CircleAlert size={22} aria-hidden="true" />
            <div>
              <strong>We couldn&apos;t complete that request</strong>
              <p>{errorMessage}</p>
              <button onClick={onRetry} type="button">
                <RefreshCw size={15} aria-hidden="true" />
                Try again
              </button>
            </div>
          </div>
        ) : null}

        {response ? <AssistantResponseSummary response={response} /> : null}
      </div>
    </div>
  )
}

function getLoadingPresentation(message: string) {
  const normalizedMessage = message.toLowerCase()
  if (normalizedMessage.includes('warning light')) {
    return {
      title: 'Searching trusted ownership guidance…',
      detail: 'Reviewing the available support documentation and sources.',
    }
  }
  if (
    normalizedMessage.includes('what service') ||
    normalizedMessage.includes('long trip') ||
    normalizedMessage.includes('recommend')
  ) {
    return {
      title: 'Preparing your service recommendation…',
      detail: 'Checking scheduled-service context and the available demo rules.',
    }
  }
  if (
    normalizedMessage.includes('due for service') ||
    normalizedMessage.includes('maintenance status')
  ) {
    return {
      title: 'Checking your vehicle status…',
      detail: 'Reviewing the selected vehicle and its scheduled-service intervals.',
    }
  }
  if (
    normalizedMessage.includes('human') ||
    normalizedMessage.includes('speak with support')
  ) {
    return {
      title: 'Preparing your support handoff…',
      detail: 'Creating a clearly labelled demo support reference.',
    }
  }
  return {
    title: 'Connecting to ownership services…',
    detail: 'This can take a little longer while the demo service wakes up.',
  }
}

function AssistantResponseSummary({ response }: { response: AssistantQueryResponse }) {
  if (response.invoked_capability === 'stored_vehicle_maintenance') {
    return <MaintenanceResultCard result={response.maintenance_result} />
  }

  if (response.invoked_capability === 'support_knowledge') {
    return <SupportResultCard result={response.support_result} />
  }

  if (response.invoked_capability === 'service_recommendation') {
    return <ServiceRecommendationCard result={response.recommendation_result} />
  }

  if (response.invoked_capability === 'human_handoff') {
    return <HandoffResultCard result={response.escalation_result} />
  }

  if (response.invoked_capability === 'experimental_predictive_maintenance_comparison') {
    return <PredictiveComparisonCard result={response.experimental_comparison_result} />
  }

  return (
    <div className="assistant-summary">
      <div className="assistant-summary__heading">
        <span>{outcomeLabels[response.outcome]}</span>
      </div>
      <p>{response.message}</p>
      {response.outcome === 'context_required' ? (
        <div className="assistant-summary__context">
          <strong>Needed to continue</strong>
          <ul>
            {response.missing_context.map((field) => (
              <li key={field}>{missingContextLabels[field]}</li>
            ))}
          </ul>
          {response.missing_context.includes('predictive_maintenance_input') ? (
            <a href="#experimental-lab">
              Open the Technical Preview to enter the model demonstration inputs.
            </a>
          ) : null}
        </div>
      ) : null}
      {response.outcome === 'unsupported' ? (
        <span className="assistant-summary__hint">
          Try asking about scheduled maintenance, service recommendations, vehicle
          support documentation, or a human handoff.
        </span>
      ) : null}
      {response.outcome === 'clarification_required' ? (
        <span className="assistant-summary__hint">
          Specify whether you need maintenance status, a service recommendation,
          support guidance, the experiment, or a human handoff.
        </span>
      ) : null}
    </div>
  )
}

const missingContextLabels = {
  vehicle_id: 'A selected vehicle',
  evaluation_date: 'An evaluation date',
  database_session: 'The maintenance service connection',
  rag_service: 'The support knowledge service',
  escalation_service: 'The demo handoff service',
  predictive_maintenance_input: 'The eight Technical Preview model inputs',
  predictive_comparison_service: 'The experimental comparison service',
} as const
