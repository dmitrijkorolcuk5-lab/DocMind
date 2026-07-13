import { NavLink, Outlet } from 'react-router-dom'

const links = [
  { to: '/documents', label: 'Documents', icon: 'D' },
  { to: '/chats', label: 'Chats', icon: 'C' },
]

export function AppLayout() {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="border-b border-slate-200 bg-ink px-5 py-5 text-white lg:min-h-screen lg:border-b-0 lg:px-6 lg:py-8">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-accent font-bold">DM</div>
          <div>
            <p className="font-semibold tracking-tight">DocMind</p>
            <p className="text-xs text-slate-400">Workspace</p>
          </div>
        </div>
        <nav aria-label="Main navigation" className="mt-6 flex gap-2 lg:mt-10 lg:flex-col">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-white/12 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`
              }
            >
              <span className="grid h-7 w-7 place-items-center rounded-lg bg-white/10 text-xs">
                {link.icon}
              </span>
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="min-w-0 px-5 py-8 sm:px-8 lg:px-12 lg:py-10">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

