import {
  ArrowUp,
  BookOpenText,
  CircleAlert,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import type { KeyboardEvent, RefObject } from 'react'
import type {
  AssistantQueryResponse,
  OrchestratedCapability,
  OrchestrationOutcome,
} from '../types/assistant'
import { HandoffResultCard } from './results/HandoffResultCard'
import { MaintenanceResultCard } from './results/MaintenanceResultCard'
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
  'What does a warning light mean?',
  'What should I check before a long trip?',
]

const capabilityLabels: Record<OrchestratedCapability, string> = {
  stored_vehicle_maintenance: 'Maintenance check',
  support_knowledge: 'Support guidance',
  human_handoff: 'Human support',
  experimental_predictive_maintenance_comparison: 'Experimental comparison',
}

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
    <section className="assistant-panel" aria-labelledby="assistant-title">
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
          placeholder="Ask about your vehicle, maintenance, or support…"
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
        Ask about maintenance, vehicle support documentation, or request a human
        handoff—all from your ownership workspace.
      </p>
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
  return (
    <div className="assistant-exchange" aria-live="polite">
      <div className="user-request">
        <span>You asked</span>
        <p>{submittedMessage}</p>
      </div>

      <div className="assistant-response">
        {isLoading ? (
          <div className="assistant-loading" role="status">
            <LoaderCircle className="spinning" size={22} aria-hidden="true" />
            <div>
              <strong>Working on your request…</strong>
              <span>The assistant is selecting the appropriate trusted service.</span>
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

function AssistantResponseSummary({ response }: { response: AssistantQueryResponse }) {
  if (response.invoked_capability === 'stored_vehicle_maintenance') {
    return <MaintenanceResultCard result={response.maintenance_result} />
  }

  if (response.invoked_capability === 'support_knowledge') {
    return <SupportResultCard result={response.support_result} />
  }

  if (response.invoked_capability === 'human_handoff') {
    return <HandoffResultCard result={response.escalation_result} />
  }

  const label = response.invoked_capability
    ? capabilityLabels[response.invoked_capability]
    : outcomeLabels[response.outcome]

  return (
    <div className="assistant-summary">
      <div className="assistant-summary__heading">
        <span>{label}</span>
        {response.invoked_capability ? (
          <small>{outcomeLabels[response.outcome]}</small>
        ) : null}
      </div>
      <p>{response.message}</p>
      {response.outcome === 'context_required' ? (
        <span className="assistant-summary__hint">
          Add the requested context and submit your question again.
        </span>
      ) : null}
    </div>
  )
}
