import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { deleteDocument, getDocuments, uploadDocument } from '../features/documents/api'
import { AsyncState } from '../shared/ui/AsyncState'

const ACCEPTED_EXTENSIONS = ['.pdf', '.txt', '.docx']

export function DocumentsPage() {
  const queryClient = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)
  const documents = useQuery({
    queryKey: ['documents'],
    queryFn: getDocuments,
    refetchInterval: (query) =>
      query.state.data?.items.some((item) => item.status === 'processing' || item.status === 'uploaded')
        ? 2000
        : false,
  })
  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: async () => {
      setError(null)
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (cause) => setError(cause instanceof Error ? cause.message : 'Upload failed'),
  })
  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0]
    if (!file) return
    const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setError('Only PDF, TXT and DOCX files are supported.')
      return
    }
    upload.mutate(file)
  }

  return (
    <section>
      <header className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold text-accent">Knowledge base</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Documents</h1>
          <p className="mt-2 text-sm text-slate-500">
            Upload files and wait until indexing finishes before using them in chats.
          </p>
        </div>
        <div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.txt,.docx"
            className="sr-only"
            onChange={(event) => handleFiles(event.target.files)}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={upload.isPending}
            className="rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:-translate-y-0.5 disabled:cursor-wait disabled:opacity-60"
          >
            {upload.isPending ? 'Uploading...' : 'Upload documents'}
          </button>
        </div>
      </header>

      <div
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          handleFiles(event.dataTransfer.files)
        }}
        className="mb-6 rounded-xl border border-dashed border-slate-300 bg-white/70 p-5 text-sm text-slate-500"
      >
        Drop a PDF, TXT or DOCX file here, or use the upload button.
      </div>

      {error && (
        <p role="alert" className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {documents.isPending && (
        <AsyncState title="Loading documents" description="Reading your document library..." />
      )}
      {documents.isError && (
        <AsyncState
          title="Could not load documents"
          description="Check that the API is running, then try again."
          tone="error"
        />
      )}
      {documents.data?.items.length === 0 && (
        <AsyncState
          title="No documents yet"
          description="Upload a document to start building your local knowledge base."
        />
      )}
      {documents.data && documents.data.items.length > 0 && (
        <div className="panel divide-y divide-slate-100 overflow-hidden">
          {documents.data.items.map((document) => (
            <article key={document.id} className="flex items-center justify-between gap-4 p-5">
              <div className="min-w-0">
                <h2 className="truncate font-semibold text-ink">{document.original_filename}</h2>
                <p className="mt-1 text-xs text-slate-500">
                  {document.mime_type} · {Math.ceil(document.size_bytes / 1024)} KB ·{' '}
                  {document.chunk_count} chunks
                </p>
                {document.error_message && (
                  <p className="mt-2 text-sm text-red-600">{document.error_message}</p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${badgeClass(document.status)}`}>
                  {document.status}
                </span>
                <button
                  type="button"
                  onClick={() => remove.mutate(document.id)}
                  disabled={remove.isPending}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:border-red-200 hover:text-red-600 disabled:cursor-wait"
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function badgeClass(status: string) {
  if (status === 'ready') return 'bg-emerald-50 text-emerald-700'
  if (status === 'failed') return 'bg-red-50 text-red-700'
  if (status === 'processing') return 'bg-amber-50 text-amber-700'
  return 'bg-slate-100 text-slate-600'
}
