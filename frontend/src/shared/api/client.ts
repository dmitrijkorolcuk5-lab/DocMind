const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

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
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorEnvelope
    throw new ApiError(body.error?.message ?? 'Request failed', response.status)
  }
  return (await response.json()) as T
}

