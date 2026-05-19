import { useState } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { Database, Search, FlaskConical, Newspaper, Crosshair, Menu, X, Sparkles, GitCompareArrows, BarChart3, Wrench, Microscope, Stethoscope } from 'lucide-react'

const LOGO_SRC = '/assets/img/logo.png'

const navigation = [
  { to: '/', label: 'Dashboard', icon: Database },
  { to: '/compounds', label: 'Compostos', icon: FlaskConical },
  { to: '/compare', label: 'Comparar', icon: GitCompareArrows },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/tools', label: 'Ferramentas', icon: Wrench },
  { to: '/articles', label: 'Artigos', icon: Newspaper },
  { to: '/targets', label: 'Targets', icon: Crosshair },
  { to: '/trials', label: 'Trials', icon: Stethoscope },
  // Histopatologia: oculta enquanto o pipeline Owkin não preenche owkin_cohort_stats/owkin_slides.
  // Rotas /histopathology e /histopathology/:cohort continuam acessíveis via URL direta.
  // { to: '/histopathology', label: 'Histopatologia', icon: Microscope },
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
            ? 'text-white bg-gradient-to-br from-green-600 to-green-900 shadow-md shadow-green-900/20'
            : 'text-gray-600 hover:bg-green-50 hover:text-green-800 border border-transparent',
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

  return (
    <div className="min-h-screen bg-white text-gray-800 font-sans">
      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 bg-white/90 backdrop-blur-lg border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-white border border-gray-200 flex items-center justify-center overflow-hidden shadow-sm">
            <img src={LOGO_SRC} alt="DrugXpert" className="w-7 h-7 object-contain" />
          </div>
          <span className="font-semibold text-gray-800">DrugXpert</span>
        </div>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-lg bg-gray-50 text-gray-700 border border-gray-200"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <div className="relative z-10 mx-auto grid min-h-screen max-w-[1440px] gap-0 lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* Sidebar */}
        <aside
          className={`
            fixed lg:sticky top-0 left-0 h-screen z-40
            w-[260px] p-4 pt-5
            transform transition-transform duration-300 lg:translate-x-0
            ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          `}
        >
          <div className="h-full bg-white rounded-2xl shadow-card border border-gray-200 p-5 flex flex-col overflow-y-auto">
            {/* Logo */}
            <div className="mb-8 animate-fade-in-up">
              <div className="flex items-center gap-3 mb-4">
                <div className="relative w-12 h-12 rounded-xl flex items-center justify-center overflow-hidden">
                  <img src={LOGO_SRC} alt="DrugXpert logo" className="w-9 h-9 object-contain" />
                </div>
                <div>
                  <h1 className="text-lg font-bold tracking-tight text-gray-800">DrugXpert</h1>
                  <p className="text-[10px] uppercase tracking-[0.2em] text-gray-400 font-medium">Scientific Explorer</p>
                </div>
              </div>
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-50 border border-green-200">
                <span
                  className="w-1.5 h-1.5 rounded-full bg-green-600"
                  style={{ animation: 'pulse-dot 2s ease-in-out infinite' }}
                />
                <span className="text-[11px] text-green-800 font-medium">ChEMBL + PubMed</span>
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
              <div className="rounded-xl bg-green-50 border-t-4 border-[#5c8d2f] p-4 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles size={14} className="text-green-700" />
                  <span className="text-xs font-semibold text-gray-700">API Endpoint</span>
                </div>
                <code className="text-[11px] text-green-800 break-all leading-relaxed font-mono">localhost:8000</code>
              </div>
            </div>
          </div>
        </aside>

        {/* Mobile overlay */}
        {mobileOpen && (
          <div className="fixed inset-0 bg-gray-900/30 z-30 lg:hidden" onClick={() => setMobileOpen(false)} />
        )}

        {/* Main content */}
        <main className="min-w-0 px-4 lg:px-6 py-6 pt-20 lg:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
