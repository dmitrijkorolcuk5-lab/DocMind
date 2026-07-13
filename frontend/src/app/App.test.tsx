import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'

function mockFetch(
  handler?: (input: RequestInfo | URL, init?: RequestInit) => Response | Promise<Response>,
) {
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

const readyDocument = {
  id: 'doc-1',
  original_filename: 'notes.txt',
  mime_type: 'text/plain',
  size_bytes: 12,
  status: 'ready',
  error_message: null,
  page_count: null,
  chunk_count: 2,
  created_at: '2026-07-13T00:00:00Z',
  updated_at: '2026-07-13T00:00:00Z',
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function streamResponse(chunks: string[]) {
  const encoder = new TextEncoder()
  return new Response(
    new ReadableStream({
      start(controller) {
        chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
        controller.close()
      },
    }),
    { status: 200, headers: { 'Content-Type': 'text/event-stream' } },
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

  it('shows the upload button and validates allowed file types', async () => {
    mockFetch()
    const user = userEvent.setup({ applyAccept: false })
    const { container } = renderApp('/documents')

    expect(await screen.findByRole('button', { name: 'Upload documents' })).toBeInTheDocument()
    const input = container.querySelector('input[type="file"]') as HTMLInputElement

    await user.upload(input, new File(['bad'], 'bad.exe', { type: 'application/octet-stream' }))

    expect(await screen.findByText('Only PDF, TXT and DOCX files are supported.')).toBeInTheDocument()
  })

  it('renders document statuses', async () => {
    mockFetch(() =>
      jsonResponse({
        items: [
          readyDocument,
          { ...readyDocument, id: 'doc-2', original_filename: 'scan.pdf', status: 'failed' },
        ],
        total: 2,
      }),
    )

    renderApp('/documents')

    expect(await screen.findByText('notes.txt')).toBeInTheDocument()
    expect(screen.getByText('ready')).toBeInTheDocument()
    expect(screen.getByText('failed')).toBeInTheDocument()
  })

  it('opens the document selector and saves ready documents', async () => {
    mockFetch((input, init) => {
      const url = String(input)
      if (url.endsWith('/documents')) return jsonResponse({ items: [readyDocument], total: 1 })
      if (url.endsWith('/chats/chat-1/documents') && init?.method === 'PUT') {
        return jsonResponse({ items: [readyDocument], total: 1 })
      }
      if (url.endsWith('/chats/chat-1/documents')) return jsonResponse({ items: [], total: 0 })
      if (url.endsWith('/chats/chat-1/messages')) return jsonResponse({ items: [], total: 0 })
      return jsonResponse({ items: [], total: 0 })
    })
    const user = userEvent.setup()
    renderApp('/chats/chat-1')

    await user.click(await screen.findByRole('button', { name: 'Select documents' }))
    await user.click(await screen.findByLabelText(/notes.txt/))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(screen.getByText('notes.txt')).toBeInTheDocument())
  })

  it('enables send with selected documents and renders streamed tokens with sources', async () => {
    let messageFetchCount = 0
    mockFetch((input, init) => {
      const url = String(input)
      if (url.endsWith('/chats/chat-1/documents')) {
        return jsonResponse({ items: [readyDocument], total: 1 })
      }
      if (url.endsWith('/documents')) return jsonResponse({ items: [readyDocument], total: 1 })
      if (url.endsWith('/chats/chat-1/messages') && !init?.method) {
        messageFetchCount += 1
        if (messageFetchCount > 1) {
          return jsonResponse({
            items: [
              {
                id: 'msg-1',
                chat_id: 'chat-1',
                role: 'assistant',
                content: 'Hello world',
                status: 'completed',
                model: 'gemini-3.1-flash-lite',
                created_at: '2026-07-13T00:00:00Z',
                sources: [
                  {
                    document_id: 'doc-1',
                    filename: 'notes.txt',
                    page_start: null,
                    page_end: null,
                    excerpt: 'Relevant excerpt',
                    score: 0.91,
                  },
                ],
              },
            ],
            total: 1,
          })
        }
        return jsonResponse({ items: [], total: 0 })
      }
      if (url.endsWith('/chats/chat-1/messages/stream')) {
        return streamResponse([
          'event: sources\ndata: {"sources":[{"document_id":"doc-1","filename":"notes.txt","page_start":null,"page_end":null,"excerpt":"Relevant excerpt","score":0.91}]}\n\n',
          'event: token\ndata: {"text":"Hello"}\n\n',
          'event: token\ndata: {"text":" world"}\n\n',
          'event: done\ndata: {"message_id":"msg-1","status":"completed"}\n\n',
        ])
      }
      return jsonResponse({ items: [], total: 0 })
    })
    const user = userEvent.setup()
    renderApp('/chats/chat-1')

    const input = await screen.findByPlaceholderText('Ask about the selected documents')
    await user.type(input, 'What is inside?')
    const button = screen.getByRole('button', { name: 'Send' })
    await waitFor(() => expect(button).toBeEnabled())
    await user.click(button)

    expect(await screen.findByText('Hello world')).toBeInTheDocument()
    expect(screen.getByText('Relevant excerpt')).toBeInTheDocument()
  })

  it('renders streaming errors only once', async () => {
    let messageFetchCount = 0
    mockFetch((input, init) => {
      const url = String(input)
      if (url.endsWith('/chats/chat-1/documents')) {
        return jsonResponse({ items: [readyDocument], total: 1 })
      }
      if (url.endsWith('/documents')) return jsonResponse({ items: [readyDocument], total: 1 })
      if (url.endsWith('/chats/chat-1/messages') && !init?.method) {
        messageFetchCount += 1
        if (messageFetchCount > 1) {
          return jsonResponse({
            items: [
              {
                id: 'msg-error',
                chat_id: 'chat-1',
                role: 'assistant',
                content: 'Gemini LLM quota was exceeded',
                status: 'failed',
                model: 'gemini-3.1-flash-lite',
                created_at: '2026-07-13T00:00:00Z',
                sources: [],
              },
            ],
            total: 1,
          })
        }
        return jsonResponse({ items: [], total: 0 })
      }
      if (url.endsWith('/chats/chat-1/messages/stream')) {
        return streamResponse([
          'event: sources\ndata: {"sources":[]}\n\n',
          'event: error\ndata: {"message":"Gemini LLM quota was exceeded"}\n\n',
        ])
      }
      return jsonResponse({ items: [], total: 0 })
    })
    const user = userEvent.setup()
    renderApp('/chats/chat-1')

    const input = await screen.findByPlaceholderText('Ask about the selected documents')
    await user.type(input, 'What is inside?')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('Gemini LLM quota was exceeded')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getAllByText('Gemini LLM quota was exceeded')).toHaveLength(1)
  })
})
