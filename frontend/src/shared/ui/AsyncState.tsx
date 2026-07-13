interface AsyncStateProps {
  title: string
  description: string
  tone?: 'neutral' | 'error'
}

export function AsyncState({ title, description, tone = 'neutral' }: AsyncStateProps) {
  return (
    <div className="panel flex min-h-64 flex-col items-center justify-center px-8 text-center">
      <div
        className={`mb-5 grid h-12 w-12 place-items-center rounded-2xl text-xl ${tone === 'error' ? 'bg-red-50 text-red-600' : 'bg-indigo-50 text-accent'}`}
      >
        {tone === 'error' ? '!' : '·'}
      </div>
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">{description}</p>
    </div>
  )
}

