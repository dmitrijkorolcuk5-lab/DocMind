import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import type { Document, Message, MessageSource } from '../entities/types'
import {
  getChatDocuments,
  getMessages,
  streamChatMessage,
  updateChatDocuments,
} from '../features/chats/api'
import { getDocuments } from '../features/documents/api'

interface SourcesEvent {
  sources: MessageSource[]
}

interface TokenEvent {
  text: string
}

export function ChatDetailsPage() {
  const { chatId = '' } = useParams()
  const queryClient = useQueryClient()
  const [selectorOpen, setSelectorOpen] = useState(false)
  const [draftSelection, setDraftSelection] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [streamingText, setStreamingText] = useState('')
  const [streamingSources, setStreamingSources] = useState<MessageSource[]>([])
  const [streamError, setStreamError] = useState<string | null>(null)

  const selected = useQuery({
    queryKey: ['chat-documents', chatId],
    queryFn: () => getChatDocuments(chatId),
    enabled: Boolean(chatId),
  })
  const documents = useQuery({ queryKey: ['documents'], queryFn: getDocuments })
  const messages = useQuery({
    queryKey: ['messages', chatId],
    queryFn: () => getMessages(chatId),
    enabled: Boolean(chatId),
  })
  const readyDocuments = useMemo(
    () => documents.data?.items.filter((document) => document.status === 'ready') ?? [],
    [documents.data],
  )
  const saveSelection = useMutation({
    mutationFn: () => updateChatDocuments(chatId, draftSelection),
    onSuccess: async () => {
      setSelectorOpen(false)
      await queryClient.invalidateQueries({ queryKey: ['chat-documents', chatId] })
    },
  })
  const send = useMutation({
    mutationFn: async (content: string) => {
      setStreamingText('')
      setStreamingSources([])
      setStreamError(null)
      await streamChatMessage(chatId, content, (event, payload) => {
        if (event === 'sources') {
          setStreamingSources((payload as SourcesEvent).sources)
        }
        if (event === 'token') {
          setStreamingText((current) => `${current}${(payload as TokenEvent).text}`)
        }
        if (event === 'error') {
          const message = (payload as { message?: string }).message ?? 'Answer generation failed'
          setStreamingText(message)
          setStreamingSources([])
          setStreamError(null)
        }
      })
    },
    onSuccess: async () => {
      setInput('')
      await queryClient.invalidateQueries({ queryKey: ['messages', chatId] })
      setStreamingText('')
      setStreamingSources([])
    },
    onError: (cause) => {
      setStreamError(cause instanceof Error ? cause.message : 'Answer generation failed')
    },
  })

  const selectedDocuments = selected.data?.items ?? []
  const canSend = input.trim().length > 0 && selectedDocuments.length > 0 && !send.isPending

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (canSend) send.mutate(input.trim())
  }

  return (
    <section className="flex min-h-[calc(100vh-5rem)] flex-col">
      <header className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <p className="text-sm font-semibold text-accent">Chat workspace</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-ink">New chat</h1>
          <p className="mt-1 text-xs text-slate-400">ID: {chatId}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {selectedDocuments.map((document) => (
              <span key={document.id} className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-accent">
                {document.original_filename}
              </span>
            ))}
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            setDraftSelection(selectedDocuments.map((document) => document.id))
            setSelectorOpen(true)
          }}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-indigo-200 hover:text-accent"
        >
          Select documents
        </button>
      </header>

      <div className="panel flex flex-1 flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.data?.items.length === 0 && !streamingText && (
            <div className="grid min-h-72 place-items-center text-center">
              <div>
                <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-indigo-50 font-bold text-accent">
                  AI
                </div>
                <h2 className="mt-5 text-lg font-semibold text-ink">Ask from selected documents</h2>
                <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
                  Select ready documents, then ask a focused question.
                </p>
              </div>
            </div>
          )}
          {messages.data?.items.map((message) => <MessageBubble key={message.id} message={message} />)}
          {streamingText && (
            <MessageBubble
              message={{
                id: 'streaming',
                chat_id: chatId,
                role: 'assistant',
                content: streamingText,
                status: 'streaming',
                model: null,
                created_at: new Date().toISOString(),
                sources: streamingSources,
              }}
            />
          )}
          {streamError && (
            <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
              {streamError}
            </p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="border-t border-slate-100 p-4">
          {selectedDocuments.length === 0 && (
            <p className="mb-2 text-xs text-slate-500">
              Upload and index documents, then select at least one before starting a chat.
            </p>
          )}
          <div className="flex gap-3 rounded-xl bg-slate-100 p-2">
            <input
              id="message"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              disabled={selectedDocuments.length === 0 || send.isPending}
              placeholder={
                selectedDocuments.length === 0
                  ? 'Select ready documents first'
                  : 'Ask about the selected documents'
              }
              className="min-w-0 flex-1 bg-transparent px-3 text-sm text-slate-700 outline-none disabled:text-slate-400"
            />
            <button
              type="submit"
              disabled={!canSend}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {send.isPending ? 'Streaming...' : 'Send'}
            </button>
          </div>
        </form>
      </div>

      {selectorOpen && (
        <DocumentSelector
          readyDocuments={readyDocuments}
          selectedIds={draftSelection}
          onChange={setDraftSelection}
          onClose={() => setSelectorOpen(false)}
          onSave={() => saveSelection.mutate()}
          saving={saveSelection.isPending}
          error={saveSelection.isError ? 'Could not save document selection.' : null}
        />
      )}
    </section>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <article className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-3xl rounded-xl px-4 py-3 ${isUser ? 'bg-accent text-white' : 'bg-slate-100 text-ink'}`}>
        <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
        {message.sources.length > 0 && (
          <div className="mt-4 border-t border-slate-200 pt-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</p>
            <ul className="mt-2 space-y-2">
              {message.sources.map((source) => (
                <li key={`${message.id}-${source.document_id}-${source.excerpt}`} className="text-xs leading-5 text-slate-600">
                  <span className="font-semibold text-slate-700">{source.filename}</span>
                  {source.page_start ? `, page ${source.page_start}` : ''} · score{' '}
                  {source.score.toFixed(2)}
                  <p className="mt-1 text-slate-500">{source.excerpt}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </article>
  )
}

function DocumentSelector({
  readyDocuments,
  selectedIds,
  onChange,
  onClose,
  onSave,
  saving,
  error,
}: {
  readyDocuments: Document[]
  selectedIds: string[]
  onChange: (ids: string[]) => void
  onClose: () => void
  onSave: () => void
  saving: boolean
  error: string | null
}) {
  const toggle = (documentId: string) => {
    onChange(
      selectedIds.includes(documentId)
        ? selectedIds.filter((id) => id !== documentId)
        : [...selectedIds, documentId],
    )
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/30 p-4">
      <div className="w-full max-w-xl rounded-xl bg-white p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">Select documents</h2>
            <p className="mt-1 text-sm text-slate-500">
              Only ready documents can be attached to this chat.
            </p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg px-2 py-1 text-slate-500 hover:bg-slate-100">
            Close
          </button>
        </div>

        {readyDocuments.length === 0 ? (
          <p className="mt-6 rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
            Upload and index documents before starting a chat.
          </p>
        ) : (
          <div className="mt-5 max-h-80 space-y-2 overflow-y-auto">
            {readyDocuments.map((document) => (
              <label
                key={document.id}
                className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 p-3 hover:border-indigo-200"
              >
                <input
                  type="checkbox"
                  checked={selectedIds.includes(document.id)}
                  onChange={() => toggle(document.id)}
                  className="h-4 w-4 accent-indigo-600"
                />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-ink">
                    {document.original_filename}
                  </span>
                  <span className="text-xs text-slate-500">{document.chunk_count} chunks</span>
                </span>
              </label>
            ))}
          </div>
        )}

        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        <div className="mt-6 flex justify-end gap-3">
          <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600">
            Cancel
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={saving || readyDocuments.length === 0}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
