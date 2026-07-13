import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'

function mockFetch(handler?: (input: RequestInfo | URL, init?: RequestInit) => Response) {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (handler) return Promise.resolve(handler(input, init))
      return Promise.resolve(
        new Response(JSON.stringify({ items: [], total: 0 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    }),
  )
}

function renderApp(path = '/documents') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[path]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('App', () => {
  it('renders the application shell', async () => {
    mockFetch()
    renderApp()

    expect(screen.getByText('DocMind')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Documents' })).toBeInTheDocument()
  })

  it('navigates between top-level pages', async () => {
    mockFetch()
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole('link', { name: /Chats/ }))

    expect(await screen.findByRole('heading', { name: 'Chats' })).toBeInTheDocument()
  })

  it('shows the documents empty state', async () => {
    mockFetch()
    renderApp('/documents')
    expect(await screen.findByRole('heading', { name: 'No documents yet' })).toBeInTheDocument()
  })

  it('shows the chats empty state', async () => {
    mockFetch()
    renderApp('/chats')
    expect(await screen.findByRole('heading', { name: 'No chats yet' })).toBeInTheDocument()
  })

  it('creates a chat and opens its workspace', async () => {
    mockFetch((_input, init) => {
      if (init?.method === 'POST') {
        return new Response(
          JSON.stringify({
            id: 'chat-123',
            title: 'New chat',
            created_at: '2026-07-13T00:00:00Z',
            updated_at: '2026-07-13T00:00:00Z',
          }),
          { status: 201, headers: { 'Content-Type': 'application/json' } },
        )
      }
      return new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    })
    const user = userEvent.setup()
    renderApp('/chats')

    await user.click(screen.getByRole('button', { name: 'New chat' }))

    await waitFor(() => expect(screen.getByText('ID: chat-123')).toBeInTheDocument())
  })
})
