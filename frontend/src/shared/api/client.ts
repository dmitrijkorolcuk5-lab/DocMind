const API_URL =
  import.meta.env.VITE_API_BASE_URL ??
  import.meta.env.VITE_API_URL ??
  'http://localhost:8000/api/v1'

interface ApiErrorEnvelope {
  error?: {
    message?: string
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: isFormData ? init?.headers : { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorEnvelope
    throw new ApiError(body.error?.message ?? 'Request failed', response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function streamRequest(
  path: string,
  body: unknown,
  onEvent: (event: string, data: unknown) => void,
): Promise<void> {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok || !response.body) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorEnvelope
    throw new ApiError(payload.error?.message ?? 'Streaming request failed', response.status)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    for (const rawEvent of events) {
      const lines = rawEvent.split('\n')
      const event = lines.find((line) => line.startsWith('event: '))?.slice(7) ?? 'message'
      const dataLine = lines.find((line) => line.startsWith('data: '))
      if (dataLine) onEvent(event, JSON.parse(dataLine.slice(6)))
    }
  }
}
