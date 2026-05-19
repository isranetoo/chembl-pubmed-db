import { useState } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { Database, Search, FlaskConical, Newspaper, Crosshair, Menu, X, Sparkles, GitCompareArrows } from 'lucide-react'

const LOGO_SRC = '/assets/img/logo.png'

const navigation = [
  { to: '/', label: 'Dashboard', icon: Database },
  { to: '/compounds', label: 'Compostos', icon: FlaskConical },
  { to: '/compare', label: 'Comparar', icon: GitCompareArrows },
  { to: '/articles', label: 'Artigos', icon: Newspaper },
  { to: '/targets', label: 'Targets', icon: Crosshair },
  { to: '/search', label: 'Busca Global', icon: Search },
]

function NavItem({ to, label, icon: Icon, onClick }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      end={to === '/'}
      className={({ isActive }) =>
        [
          'group flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-300',
          isActive
            ? 'bg-gradient-to-r from-emerald-500/20 to-teal-500/10 text-emerald-300 border border-emerald-500/20 shadow-lg shadow-emerald-500/5'
            : 'text-white/50 hover:bg-white/[0.06] hover:text-white/90 border border-transparent',
        ].join(' ')
      }
    >
      <Icon size={18} className="transition-transform duration-300 group-hover:scale-110" />
      <span>{label}</span>
    </NavLink>
  )
}

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background orbs */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute -top-40 -left-40 w-[500px] h-[500px] bg-emerald-600/[0.07] rounded-full blur-[120px] animate-float" />
        <div className="absolute top-1/2 -right-32 w-[400px] h-[400px] bg-teal-500/[0.05] rounded-full blur-[100px]" style={{ animationDelay: '2s', animation: 'float 7s ease-in-out infinite' }} />
        <div className="absolute -bottom-20 left-1/3 w-[350px] h-[350px] bg-cyan-500/[0.04] rounded-full blur-[100px]" style={{ animationDelay: '4s', animation: 'float 6s ease-in-out infinite' }} />
      </div>

      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 bg-slate-950/80 backdrop-blur-xl border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center overflow-hidden">
            <img src={LOGO_SRC} alt="DrugXpert" className="w-7 h-7 object-contain" />
          </div>
          <span className="font-semibold text-sm" style={{ fontFamily: 'Outfit' }}>DrugXpert</span>
        </div>
        <button onClick={() => setMobileOpen(!mobileOpen)} className="p-2 rounded-lg bg-white/5 text-white/70">
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <div className="relative z-10 mx-auto grid min-h-screen max-w-[1440px] gap-0 lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* Sidebar */}
        <aside className={`
          fixed lg:sticky top-0 left-0 h-screen z-40
          w-[260px] p-4 pt-5
          transform transition-transform duration-300 lg:translate-x-0
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          <div className="h-full glass rounded-2xl p-5 flex flex-col overflow-y-auto">
            {/* Logo */}
            <div className="mb-8 animate-fade-in-up">
              <div className="flex items-center gap-3 mb-4">
                <div className="relative w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-400/15 to-teal-500/10 border border-emerald-500/20 flex items-center justify-center shadow-lg shadow-emerald-500/10 overflow-hidden">
                  <img src={LOGO_SRC} alt="DrugXpert logo" className="w-9 h-9 object-contain" />
                </div>
                <div>
                  <h1 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Outfit' }}>DrugXpert</h1>
                  <p className="text-[10px] uppercase tracking-[0.2em] text-white/30 font-medium">Scientific Explorer</p>
                </div>
              </div>
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/[0.08] border border-emerald-500/[0.15]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" style={{ animation: 'pulse-dot 2s ease-in-out infinite' }} />
                <span className="text-[11px] text-emerald-300/80">ChEMBL + PubMed</span>
              </div>
            </div>

            {/* Nav */}
            <nav className="space-y-1.5 flex-1">
              {navigation.map((item, i) => (
                <div key={item.to} className="animate-fade-in-up" style={{ animationDelay: `${(i + 1) * 0.06}s` }}>
                  <NavItem {...item} onClick={() => setMobileOpen(false)} />
                </div>
              ))}
            </nav>

            {/* Footer */}
            <div className="mt-auto pt-6 animate-fade-in" style={{ animationDelay: '0.4s' }}>
              <div className="rounded-xl bg-gradient-to-br from-emerald-500/[0.08] to-teal-500/[0.04] border border-white/[0.06] p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles size={14} className="text-emerald-400" />
                  <span className="text-xs font-semibold text-white/70">API Endpoint</span>
                </div>
                <code className="text-[11px] text-emerald-300/60 break-all leading-relaxed">localhost:8000</code>
              </div>
            </div>
          </div>
        </aside>

        {/* Mobile overlay */}
        {mobileOpen && (
          <div className="fixed inset-0 bg-black/60 z-30 lg:hidden" onClick={() => setMobileOpen(false)} />
        )}

        {/* Main content */}
        <main className="min-w-0 px-4 lg:px-6 py-6 pt-20 lg:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
