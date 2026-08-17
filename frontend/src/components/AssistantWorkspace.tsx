import { ArrowUp, BookOpenText, MessageSquareText, Sparkles } from 'lucide-react'

interface AssistantWorkspaceProps {
  draft: string
  onDraftChange: (draft: string) => void
}

const suggestedQuestions = [
  'Is my vehicle due for service?',
  'What does a warning light mean?',
  'What should I check before a long trip?',
]

export function AssistantWorkspace({
  draft,
  onDraftChange,
}: AssistantWorkspaceProps) {
  return (
    <section className="assistant-panel" aria-labelledby="assistant-title">
      <div className="assistant-panel__topline">
        <span className="assistant-identity">
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

      <div className="assistant-panel__welcome">
        <div className="assistant-symbol" aria-hidden="true">
          <MessageSquareText size={28} strokeWidth={1.5} />
        </div>
        <p className="section-label">Here for the road ahead</p>
        <h2 id="assistant-title">How can I help with your vehicle today?</h2>
        <p>
          Ask about maintenance, vehicle support documentation, or request a human
          handoff—all from your ownership workspace.
        </p>
      </div>

      <div className="suggested-prompts" aria-label="Suggested questions">
        {suggestedQuestions.map((question) => (
          <button key={question} onClick={() => onDraftChange(question)} type="button">
            {question}
          </button>
        ))}
      </div>

      <div className="assistant-composer">
        <label className="visually-hidden" htmlFor="assistant-question">
          Ask the ownership assistant
        </label>
        <textarea
          id="assistant-question"
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="Ask about your vehicle, maintenance, or support…"
          rows={3}
          value={draft}
        />
        <button
          aria-label="Send question (available after assistant connection)"
          className="send-button"
          disabled
          title="Live assistant connection is not enabled yet"
          type="button"
        >
          <ArrowUp size={20} aria-hidden="true" />
        </button>
      </div>

      <div className="assistant-panel__footer">
        <span>Preview interface · Live responses are not connected yet</span>
        <span>Responses will use trusted services and documentation</span>
      </div>
    </section>
  )
}
