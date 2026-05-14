import { Link } from 'react-router-dom'
import { ArrowRight, FlaskConical, Search, Crosshair, Newspaper, Activity, Sparkles, TrendingUp, Shield, BookOpen } from 'lucide-react'
import { useStats } from '../lib/hooks'
import { formatNumber } from '../lib/utils'
import StatCard from '../components/StatCard'
import Loader from '../components/Loader'
import Section from '../components/Section'

export default function HomePage() {
  const { data, isLoading, error } = useStats()

  if (isLoading) return <Loader label="Carregando estatísticas do banco..." />
  if (error) return (
    <div className="glass-card p-6 border-red-500/20 animate-fade-in">
      <p className="text-red-300 text-sm">{error.message}</p>
    </div>
  )

  return (
    <div className="space-y-6 pb-8">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-emerald-600/20 via-teal-600/10 to-cyan-600/5 border border-emerald-500/10 p-8 lg:p-10 animate-fade-in-up">
        <div className="absolute -top-20 -right-20 w-64 h-64 bg-emerald-500/10 rounded-full blur-[80px]" />
        <div className="absolute -bottom-10 -left-10 w-48 h-48 bg-teal-500/10 rounded-full blur-[60px]" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-4">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" style={{ animation: 'pulse-dot 2s ease-in-out infinite' }} />
              <span className="text-[11px] font-semibold text-emerald-300/80 uppercase tracking-wider">Banco ativo</span>
            </div>
            <h1 className="text-3xl lg:text-4xl font-bold tracking-tight mb-3" style={{ fontFamily: 'Outfit' }}>
              <span className="text-white">Explore compostos,</span>
              <br />
              <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                descubra evidências.
              </span>
            </h1>
            <p className="text-sm lg:text-base text-white/40 leading-relaxed max-w-md">
              Navegue por dados farmacológicos do ChEMBL e literatura científica do PubMed em uma interface unificada.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link to="/compounds"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-slate-950 bg-gradient-to-r from-emerald-400 to-teal-400 transition-all duration-300 hover:shadow-lg hover:shadow-emerald-500/25 hover:scale-[1.02] active:scale-[0.98]">
              Explorar compostos <ArrowRight size={16} />
            </Link>
            <Link to="/search"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-medium text-white/80 border border-white/15 bg-white/[0.04] transition-all duration-300 hover:bg-white/[0.08] hover:border-white/25">
              <Search size={16} /> Buscar
            </Link>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Compostos" value={data.compounds} icon={FlaskConical} color="emerald" delay={0.05} />
        <StatCard label="Artigos" value={data.articles} icon={BookOpen} color="sky" delay={0.1}
          helper={`${formatNumber(data.articles_with_abstract)} com abstract`} />
        <StatCard label="Indicações aprovadas" value={data.approved_indications} icon={Shield} color="amber" delay={0.15}
          helper={`${formatNumber(data.indications)} total`} />
        <StatCard label="Targets" value={data.targets} icon={Crosshair} color="violet" delay={0.2}
          helper={`QED médio: ${data.avg_qed ?? '—'}`} />
      </div>

      {/* Features grid */}
      <div className="grid gap-4 lg:grid-cols-3">
        {[
          {
            icon: FlaskConical, color: 'emerald',
            title: 'Compound Explorer',
            desc: 'Filtre por fase clínica, QED, peso molecular, Lipinski e muito mais.',
            link: '/compounds',
          },
          {
            icon: Search, color: 'sky',
            title: 'Busca Full-Text',
            desc: 'Encontre compostos, artigos e targets usando busca unificada por relevância.',
            link: '/search',
          },
          {
            icon: Activity, color: 'amber',
            title: 'Perfis Completos',
            desc: 'ADMET, indicações, mecanismos de ação, bioatividades e literatura em uma tela.',
            link: '/compounds',
          },
        ].map((item, i) => (
          <Link to={item.link} key={item.title}
            className="glass-card group p-6 animate-fade-in-up cursor-pointer hover:scale-[1.01]"
            style={{ animationDelay: `${(i + 3) * 0.08}s` }}>
            <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${
              item.color === 'emerald' ? 'from-emerald-400 to-emerald-600' :
              item.color === 'sky' ? 'from-sky-400 to-sky-600' :
              'from-amber-400 to-amber-600'
            } flex items-center justify-center shadow-lg mb-4 transition-transform duration-300 group-hover:scale-110`}>
              <item.icon size={20} className="text-white" />
            </div>
            <h3 className="text-base font-bold text-white/90 mb-2" style={{ fontFamily: 'Outfit' }}>{item.title}</h3>
            <p className="text-sm text-white/35 leading-relaxed">{item.desc}</p>
            <div className="mt-4 flex items-center gap-1 text-xs font-medium text-emerald-400/60 group-hover:text-emerald-400 transition-colors">
              Acessar <ArrowRight size={12} className="transition-transform group-hover:translate-x-1" />
            </div>
          </Link>
        ))}
      </div>

      {/* Quick stats row */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Banco de dados" delay={0.3}>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Mecanismos', value: data.mechanisms },
              { label: 'Bioatividades', value: data.bioactivities },
              { label: 'Com ADMET', value: data.compounds_with_admet },
              { label: 'Ano mais recente', value: data.latest_article_year },
            ].map((s) => (
              <div key={s.label} className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
                <p className="text-[10px] uppercase tracking-wider text-white/30 mb-1">{s.label}</p>
                <p className="text-xl font-bold text-white/80" style={{ fontFamily: 'Outfit' }}>{formatNumber(s.value)}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Endpoints da API" delay={0.35}>
          <div className="space-y-2">
            {[
              '/compounds — Listagem e filtros',
              '/articles — Literatura científica',
              '/targets — Alvos biológicos',
              '/search — Full-text unificada',
              '/stats — Métricas do banco',
              '/compounds/{id}/admet — ADMET',
            ].map((ep) => (
              <div key={ep} className="flex items-center gap-3 rounded-lg bg-white/[0.02] border border-white/[0.04] px-3 py-2.5 text-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/60 flex-shrink-0" />
                <code className="text-white/50 font-mono">{ep}</code>
              </div>
            ))}
          </div>
        </Section>
      </div>
    </div>
  )
}
