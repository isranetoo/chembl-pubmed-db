import { Outlet, NavLink } from 'react-router-dom'
import { Database, Search, FlaskConical, Newspaper, Crosshair, Github } from 'lucide-react'

const navigation = [
  { to: '/', label: 'Dashboard', icon: Database },
  { to: '/compounds', label: 'Compostos', icon: FlaskConical },
  { to: '/articles', label: 'Artigos', icon: Newspaper },
  { to: '/targets', label: 'Targets', icon: Crosshair },
  { to: '/search', label: 'Busca global', icon: Search },
]

function NavItem({ to, label, icon: Icon }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          'flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition',
          isActive
            ? 'bg-brand-500/15 text-brand-200 ring-1 ring-brand-400/30'
            : 'text-slate-400 hover:bg-white/5 hover:text-white',
        ].join(' ')
      }
    >
      <Icon size={18} />
      <span>{label}</span>
    </NavLink>
  )
}

export default function AppLayout() {
  return (
    <div className="min-h-screen">
      <div className="mx-auto grid min-h-screen max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[270px_minmax(0,1fr)] lg:px-6">
        <aside className="h-fit rounded-3xl border border-white/10 bg-slate-900/70 p-5 shadow-soft backdrop-blur">
          <div className="mb-8">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-300">Scientific explorer</p>
            <h1 className="mt-3 text-2xl font-semibold text-white">ChEMBL + PubMed DB</h1>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Frontend web para explorar compostos, propriedades ADMET, artigos científicos e alvos biológicos do repositório.
            </p>
          </div>

          <nav className="space-y-2">
            {navigation.map((item) => (
              <NavItem key={item.to} {...item} />
            ))}
          </nav>

          <div className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400">
            <p className="font-medium text-white">API esperada</p>
            <p className="mt-2 leading-6">VITE_API_BASE_URL=http://localhost:8000</p>
          </div>

          <a
            href="https://github.com/isranetoo/chembl-pubmed-db"
            target="_blank"
            rel="noreferrer"
            className="mt-4 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
          >
            <Github size={16} /> Ver repositório
          </a>
        </aside>

        <main className="min-w-0 py-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
