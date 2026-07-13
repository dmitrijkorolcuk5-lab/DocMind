import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

import { createChat, getChats } from '../features/chats/api'
import { AsyncState } from '../shared/ui/AsyncState'

export function ChatsPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const chats = useQuery({ queryKey: ['chats'], queryFn: getChats })
  const create = useMutation({
    mutationFn: () => createChat('New chat'),
    onSuccess: async (chat) => {
      await queryClient.invalidateQueries({ queryKey: ['chats'] })
      navigate(`/chats/${chat.id}`)
    },
  })

  return (
    <section>
      <header className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-accent">Conversations</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Chats</h1>
          <p className="mt-2 text-sm text-slate-500">Create a workspace for document-grounded answers.</p>
        </div>
        <button
          type="button"
          onClick={() => create.mutate()}
          disabled={create.isPending}
          className="rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-200 transition hover:-translate-y-0.5 disabled:cursor-wait disabled:opacity-60"
        >
          {create.isPending ? 'Creating…' : 'New chat'}
        </button>
      </header>

      {create.isError && (
        <p role="alert" className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
          Chat creation failed. Please try again.
        </p>
      )}
      {chats.isPending && <AsyncState title="Loading chats" description="Fetching conversations…" />}
      {chats.isError && (
        <AsyncState
          title="Could not load chats"
          description="Check that the API is running, then try again."
          tone="error"
        />
      )}
      {chats.data?.items.length === 0 && (
        <AsyncState
          title="No chats yet"
          description="Create your first chat. Documents can be connected in the next phase."
        />
      )}
      {chats.data && chats.data.items.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {chats.data.items.map((chat) => (
            <Link
              to={`/chats/${chat.id}`}
              key={chat.id}
              className="panel p-5 transition hover:-translate-y-1 hover:border-indigo-200"
            >
              <div className="mb-8 grid h-10 w-10 place-items-center rounded-xl bg-indigo-50 text-sm font-bold text-accent">
                C
              </div>
              <h2 className="font-semibold text-ink">{chat.title}</h2>
              <p className="mt-1 text-xs text-slate-500">
                Updated {new Date(chat.updated_at).toLocaleDateString()}
              </p>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}

