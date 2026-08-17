export type ApiErrorKind = 'http_error' | 'network_error' | 'invalid_response'

export class ApiClientError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number | null
  readonly detail: string

  constructor(
    kind: ApiErrorKind,
    detail: string,
    status: number | null = null,
    options?: ErrorOptions,
  ) {
    super(detail, options)
    this.name = 'ApiClientError'
    this.kind = kind
    this.status = status
    this.detail = detail
  }
}

type ResponseParser<TResponse> = (payload: unknown) => TResponse

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const apiBaseUrl = trimTrailingSlash(configuredApiBaseUrl || '/api')

export async function postJson<TRequest, TResponse>(
  path: string,
  request: TRequest,
  parseResponse: ResponseParser<TResponse>,
): Promise<TResponse> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${ensureLeadingSlash(path)}`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })
  } catch (error) {
    throw new ApiClientError(
      'network_error',
      'The backend service could not be reached.',
      null,
      { cause: error },
    )
  }

  const payload = await readJsonPayload(response)
  if (!response.ok) {
    throw new ApiClientError(
      'http_error',
      extractErrorDetail(payload, response.status),
      response.status,
    )
  }

  try {
    return parseResponse(payload)
  } catch (error) {
    throw new ApiClientError(
      'invalid_response',
      'The backend returned an unexpected response.',
      response.status,
      { cause: error },
    )
  }
}

async function readJsonPayload(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch (error) {
    if (response.ok) {
      throw new ApiClientError(
        'invalid_response',
        'The backend returned an empty or malformed JSON response.',
        response.status,
        { cause: error },
      )
    }
    return null
  }
}

function extractErrorDetail(payload: unknown, status: number): string {
  if (isRecord(payload) && typeof payload.detail === 'string') {
    return payload.detail
  }
  if (isRecord(payload) && Array.isArray(payload.detail)) {
    return 'The request did not pass backend validation.'
  }
  return `The backend request failed with status ${status}.`
}

function ensureLeadingSlash(path: string): string {
  return path.startsWith('/') ? path : `/${path}`
}

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
