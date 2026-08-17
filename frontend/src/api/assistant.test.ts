import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryAssistant } from './assistant'
import { ApiClientError } from './client'
import type { AssistantQueryResponse } from '../types/assistant'

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
    answer: 'Consult the documented warning-light guidance.',
    retrieval_status: 'supported',
    sources: [
      {
        source_id: 'warning-lights',
        document_title: 'Warning Light Guidance',
        section_title: 'General response',
        chunk_id: 'warning-lights-general-response-1',
      },
    ],
  },
  escalation_result: null,
  experimental_comparison_result: null,
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('queryAssistant', () => {
  it('posts the typed request and returns a validated structured response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(supportResponse),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await queryAssistant({
      message: 'What does a warning light mean?',
      vehicle_id: 1,
    })

    expect(fetchMock).toHaveBeenCalledWith('/api/assistant/query', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'What does a warning light mean?',
        vehicle_id: 1,
      }),
    })
    expect(response.invoked_capability).toBe('support_knowledge')
    if (response.invoked_capability === 'support_knowledge') {
      expect(response.support_result.sources[0]?.source_id).toBe('warning-lights')
    }
  })

  it('surfaces non-success responses as typed HTTP errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: 'Vehicle was not found' }, 404),
      ),
    )

    const error = await queryAssistant({
      message: 'Is my vehicle due for service?',
      vehicle_id: 99,
    }).catch((reason: unknown) => reason)

    expect(error).toBeInstanceOf(ApiClientError)
    expect(error).toMatchObject({
      kind: 'http_error',
      status: 404,
      detail: 'Vehicle was not found',
    })
  })

  it('rejects a successful response with an inconsistent capability payload', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          ...supportResponse,
          support_result: null,
        }),
      ),
    )

    const error = await queryAssistant({ message: 'Explain a warning light' }).catch(
      (reason: unknown) => reason,
    )

    expect(error).toMatchObject({
      kind: 'invalid_response',
      status: 200,
    })
  })

  it('rejects an empty successful response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    )

    const error = await queryAssistant({ message: 'Explain a warning light' }).catch(
      (reason: unknown) => reason,
    )

    expect(error).toMatchObject({
      kind: 'invalid_response',
      status: 204,
      detail: 'The backend returned an empty or malformed JSON response.',
    })
  })

  it('wraps fetch failures as typed network errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))

    const error = await queryAssistant({ message: 'Explain a warning light' }).catch(
      (reason: unknown) => reason,
    )

    expect(error).toMatchObject({
      kind: 'network_error',
      status: null,
    })
  })
})

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
