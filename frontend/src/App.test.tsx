import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { queryAssistant } from './api/assistant'
import { ApiClientError } from './api/client'
import App from './App'
import type { AssistantQueryResponse } from './types/assistant'

vi.mock('./api/assistant', () => ({
  queryAssistant: vi.fn(),
}))

const queryAssistantMock = vi.mocked(queryAssistant)

const supportResponse: AssistantQueryResponse = {
  routing_decision: {
    intent: 'support_knowledge',
    normalized_request: 'what does a warning light mean',
    matched_intents: ['support_knowledge'],
    reason: 'The request asks for automotive support information.',
  },
  outcome: 'executed',
  invoked_capability: 'support_knowledge',
  missing_context: [],
  message: 'Support knowledge was retrieved and grounded.',
  maintenance_result: null,
  support_result: {
    answer: 'The support guide explains how to respond to the warning indicator.',
    retrieval_status: 'supported',
    sources: [
      {
        source_id: 'warning-indicators',
        document_title: 'Warning Indicator Guide',
        section_title: 'Responding to dashboard warnings',
        chunk_id: 'warning-indicators-responding-01',
      },
    ],
  },
  escalation_result: null,
  experimental_comparison_result: null,
}

const maintenanceResponse: AssistantQueryResponse = {
  routing_decision: {
    intent: 'stored_vehicle_maintenance',
    normalized_request: 'is my vehicle due for service',
    matched_intents: ['stored_vehicle_maintenance'],
    reason: 'The request asks for the selected vehicle maintenance status.',
  },
  outcome: 'executed',
  invoked_capability: 'stored_vehicle_maintenance',
  missing_context: [],
  message: 'Stored-vehicle maintenance was evaluated deterministically.',
  maintenance_result: {
    status: 'due_soon',
    kilometres_travelled_since_last_service: 8_100,
    kilometres_remaining: 1_900,
    months_remaining: 2,
    reasons: ['Distance interval is approaching its service threshold.'],
  },
  support_result: null,
  escalation_result: null,
  experimental_comparison_result: null,
}

const handoffResponse: AssistantQueryResponse = {
  routing_decision: {
    intent: 'human_handoff',
    normalized_request: 'i want to speak with support',
    matched_intents: ['human_handoff'],
    reason: 'The user explicitly requested human support.',
  },
  outcome: 'executed',
  invoked_capability: 'human_handoff',
  missing_context: [],
  message: 'A demo human handoff was created.',
  maintenance_result: null,
  support_result: null,
  escalation_result: {
    ticket_id: 'DEMO-OWNERSHIP-1042',
    reason: 'routed_human_handoff',
    request_summary: 'I want to speak with support.',
    status: 'created',
  },
  experimental_comparison_result: null,
}

const predictiveResponse: AssistantQueryResponse = {
  routing_decision: {
    intent: 'experimental_predictive_maintenance',
    normalized_request: 'show the experimental maintenance comparison',
    matched_intents: ['experimental_predictive_maintenance'],
    reason: 'The request explicitly asks for the experimental comparison.',
  },
  outcome: 'executed',
  invoked_capability: 'experimental_predictive_maintenance_comparison',
  missing_context: [],
  message: 'The experimental comparison was completed.',
  maintenance_result: null,
  support_result: null,
  escalation_result: null,
  experimental_comparison_result: {
    deterministic: {
      status: 'not_due',
      kilometres_travelled_since_last_service: 2_500,
      kilometres_remaining: 7_500,
      months_remaining: 8,
      reasons: ['Distance and time intervals remain below their thresholds.'],
    },
    experimental_ml: {
      maintenance_needed_within_90_days_prediction: 0,
      positive_class_probability: 0.12,
      threshold: 0.19,
      experimental: true,
      artifact_schema_version: 1,
    },
    comparison: {
      deterministic_binary_signal: 0,
      experimental_ml_binary_signal: 0,
      relationship: 'agree_negative',
    },
  },
}

beforeEach(() => {
  queryAssistantMock.mockReset()
})

describe('App', () => {
  it('renders truthful seeded vehicle context and the assistant workspace', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'Aster Motors Comet' }),
    ).toBeInTheDocument()
    expect(screen.getByText('12,500 km')).toBeInTheDocument()
    expect(screen.getByText('15 Jul 2026')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', {
        name: 'How can I help with your vehicle today?',
      }),
    ).toBeInTheDocument()
  })

  it('places a selected quick action into and focuses the assistant composer', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /check service status/i }))

    const composer = screen.getByLabelText('Ask the ownership assistant')
    expect(composer).toHaveValue('Is my vehicle due for service?')
    expect(composer).toHaveFocus()
  })

  it('does not submit blank input', () => {
    render(<App />)

    fireEvent.submit(screen.getByRole('form', { name: 'Assistant question form' }))

    expect(queryAssistantMock).not.toHaveBeenCalled()
  })

  it('submits with Enter and displays the latest grounded response', async () => {
    queryAssistantMock.mockResolvedValue(supportResponse)
    render(<App />)

    const composer = screen.getByLabelText('Ask the ownership assistant')
    fireEvent.change(composer, {
      target: { value: 'What does a warning light mean?' },
    })
    fireEvent.keyDown(composer, { key: 'Enter', code: 'Enter' })

    await waitFor(() => {
      expect(queryAssistantMock).toHaveBeenCalledWith({
        message: 'What does a warning light mean?',
        vehicle_id: 1,
      })
    })
    expect(screen.getByText('You asked')).toBeInTheDocument()
    expect(
      await screen.findByText(
        'The support guide explains how to respond to the warning indicator.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Grounded support answer')).toBeInTheDocument()
    expect(screen.getByText('Warning Indicator Guide')).toBeInTheDocument()
    expect(screen.getByText('Responding to dashboard warnings')).toBeInTheDocument()
    expect(screen.queryByText('Support knowledge was retrieved and grounded.')).not.toBeInTheDocument()
  })

  it('uses the dedicated authoritative card for a maintenance response', async () => {
    queryAssistantMock.mockResolvedValue(maintenanceResponse)
    render(<App />)

    fireEvent.change(screen.getByLabelText('Ask the ownership assistant'), {
      target: { value: 'Is my vehicle due for service?' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))

    expect(
      await screen.findByLabelText('Authoritative scheduled maintenance result'),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Due Soon' })).toBeInTheDocument()
    expect(screen.getByText('1,900 km')).toBeInTheDocument()
    expect(
      screen.queryByText('Stored-vehicle maintenance was evaluated deterministically.'),
    ).not.toBeInTheDocument()
  })

  it('uses the dedicated demo card for a human handoff response', async () => {
    queryAssistantMock.mockResolvedValue(handoffResponse)
    render(<App />)

    fireEvent.change(screen.getByLabelText('Ask the ownership assistant'), {
      target: { value: 'I want to speak with support.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))

    const handoffCard = await screen.findByLabelText('Demo human handoff result')
    expect(handoffCard).toBeInTheDocument()
    expect(screen.getByText('DEMO-OWNERSHIP-1042')).toBeInTheDocument()
    expect(within(handoffCard).getByText('I want to speak with support.')).toBeInTheDocument()
    expect(screen.queryByText('A demo human handoff was created.')).not.toBeInTheDocument()
  })

  it('uses the dedicated comparison card for an experimental predictive response', async () => {
    queryAssistantMock.mockResolvedValue(predictiveResponse)
    render(<App />)

    fireEvent.change(screen.getByLabelText('Ask the ownership assistant'), {
      target: { value: 'Show the experimental maintenance comparison.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))

    expect(
      await screen.findByLabelText('Experimental predictive maintenance comparison'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Experimental model output')).toHaveTextContent(
      'Experimental',
    )
    expect(screen.getByLabelText('Authoritative scheduled maintenance result')).toBeInTheDocument()
    expect(screen.getByText('12%')).toBeInTheDocument()
    expect(screen.queryByText('The experimental comparison was completed.')).not.toBeInTheDocument()
  })

  it('keeps an unavailable experimental artifact on the honest error path', async () => {
    queryAssistantMock.mockRejectedValue(
      new ApiClientError('http_error', 'Internal artifact location unavailable.', 503),
    )
    render(<App />)

    fireEvent.change(screen.getByLabelText('Ask the ownership assistant'), {
      target: { value: 'Show the experimental maintenance comparison.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))

    expect(
      await screen.findByText('That capability is temporarily unavailable. Please try again later.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Internal artifact location unavailable.')).not.toBeInTheDocument()
    expect(
      screen.queryByLabelText('Experimental predictive maintenance comparison'),
    ).not.toBeInTheDocument()
  })

  it('shows a neutral loading state and prevents duplicate submissions', async () => {
    let resolveRequest: (response: AssistantQueryResponse) => void = () => undefined
    const pendingRequest = new Promise<AssistantQueryResponse>((resolve) => {
      resolveRequest = resolve
    })
    queryAssistantMock.mockReturnValue(pendingRequest)
    render(<App />)

    const composer = screen.getByLabelText('Ask the ownership assistant')
    const form = screen.getByRole('form', { name: 'Assistant question form' })
    fireEvent.change(composer, { target: { value: 'Explain a warning light' } })
    fireEvent.submit(form)
    fireEvent.submit(form)

    expect(screen.getByText('Working on your request…')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Request in progress' })).toBeDisabled()
    expect(queryAssistantMock).toHaveBeenCalledTimes(1)

    resolveRequest(supportResponse)
    expect(await screen.findByText('Support guidance')).toBeInTheDocument()
  })

  it('shows a friendly typed API error and allows retry', async () => {
    queryAssistantMock
      .mockRejectedValueOnce(
        new ApiClientError(
          'network_error',
          'The backend service could not be reached.',
        ),
      )
      .mockResolvedValueOnce(supportResponse)
    render(<App />)

    fireEvent.change(screen.getByLabelText('Ask the ownership assistant'), {
      target: { value: 'Explain a warning light' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))

    expect(
      await screen.findByText(
        'The assistant could not reach the backend service. Check that it is running and try again.',
      ),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => expect(queryAssistantMock).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('Support guidance')).toBeInTheDocument()
  })

  it.each([
    {
      outcome: 'context_required' as const,
      message: 'Stored-vehicle maintenance requires additional context.',
      expectedLabel: 'More information needed',
    },
    {
      outcome: 'unsupported' as const,
      message: 'This request is outside the supported automotive scope.',
      expectedLabel: 'Outside available support',
    },
  ])('renders the $outcome orchestration outcome honestly', async (scenario) => {
    queryAssistantMock.mockResolvedValue({
      routing_decision: {
        intent:
          scenario.outcome === 'unsupported'
            ? 'unsupported'
            : 'stored_vehicle_maintenance',
        normalized_request: 'request',
        matched_intents: [],
        reason: 'Deterministic routing result.',
      },
      outcome: scenario.outcome,
      invoked_capability: null,
      missing_context:
        scenario.outcome === 'context_required' ? ['vehicle_id'] : [],
      message: scenario.message,
      maintenance_result: null,
      support_result: null,
      escalation_result: null,
      experimental_comparison_result: null,
    })
    render(<App />)

    fireEvent.change(screen.getByLabelText('Ask the ownership assistant'), {
      target: { value: 'request' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))

    expect(await screen.findByText(scenario.expectedLabel)).toBeInTheDocument()
    expect(screen.getByText(scenario.message)).toBeInTheDocument()
  })
})
