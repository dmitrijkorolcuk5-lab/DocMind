import { useParams } from 'react-router-dom'

export function ChatDetailsPage() {
  const { chatId } = useParams()

  return (
    <section className="flex min-h-[calc(100vh-5rem)] flex-col">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-accent">Chat workspace</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-ink">New chat</h1>
          <p className="mt-1 text-xs text-slate-400">ID: {chatId}</p>
        </div>
        <button disabled className="cursor-not-allowed rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-400">
          Select documents
        </button>
      </header>

      <div className="panel flex flex-1 flex-col">
        <div className="grid flex-1 place-items-center p-8 text-center">
          <div>
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-indigo-50 font-bold text-accent">AI</div>
            <h2 className="mt-5 text-lg font-semibold text-ink">Messages will appear here</h2>
            <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">Document selection, retrieval and streamed answers are intentionally reserved for the next phase.</p>
          </div>
        </div>
        <div className="border-t border-slate-100 p-4">
          <label htmlFor="message" className="sr-only">Message</label>
          <div className="flex gap-3 rounded-xl bg-slate-100 p-2">
            <input id="message" disabled placeholder="RAG chat is coming in the next phase" className="min-w-0 flex-1 bg-transparent px-3 text-sm text-slate-500 outline-none" />
            <button disabled className="cursor-not-allowed rounded-lg bg-slate-300 px-4 py-2 text-sm font-semibold text-white">Send</button>
          </div>
        </div>
      </div>
    </section>
  )
}

