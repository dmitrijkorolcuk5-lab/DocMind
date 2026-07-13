import { useQuery } from '@tanstack/react-query'

import { getDocuments } from '../features/documents/api'
import { AsyncState } from '../shared/ui/AsyncState'

export function DocumentsPage() {
  const documents = useQuery({ queryKey: ['documents'], queryFn: getDocuments })

  return (
    <section>
      <header className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold text-accent">Knowledge base</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Documents</h1>
          <p className="mt-2 text-sm text-slate-500">Files available to your future RAG chats.</p>
        </div>
        <button
          disabled
          title="Document upload will be added in the next phase"
          className="cursor-not-allowed rounded-xl bg-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-500"
        >
          Upload coming next
        </button>
      </header>

      {documents.isPending && (
        <AsyncState title="Loading documents" description="Reading your document library…" />
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
          description="The upload and indexing pipeline will land in the next implementation phase."
        />
      )}
      {documents.data && documents.data.items.length > 0 && (
        <div className="panel divide-y divide-slate-100 overflow-hidden">
          {documents.data.items.map((document) => (
            <article key={document.id} className="flex items-center justify-between gap-4 p-5">
              <div className="min-w-0">
                <h2 className="truncate font-semibold text-ink">{document.original_filename}</h2>
                <p className="mt-1 text-xs text-slate-500">
                  {document.mime_type} · {Math.ceil(document.size_bytes / 1024)} KB
                </p>
              </div>
              <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-accent">
                {document.status}
              </span>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

