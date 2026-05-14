import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useGlobalSearch } from '../lib/hooks'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Pill from '../components/Pill'
import Section from '../components/Section'
import { formatNumber } from '../lib/utils'
import { Search, ArrowUpRight, FlaskConical, BookOpen, Crosshair, Sparkles } from 'lucide-react'

const sourceConfig = {
  compound: { icon: FlaskConical, color: 'emerald', label: 'Composto' },
  article:  { icon: BookOpen,     color: 'sky',     label: 'Artigo' },
  target:   { icon: Crosshair,    color: 'violet',  label: 'Target' },
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [source, setSource] = useState('')

  const { data, isLoading, error } = useGlobalSearch({
    q: submittedQuery,
    source: source || undefined,
    size: 20, page: 1,
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim()) setSubmittedQuery(query.trim())
  }

  return (
    <div className="space-y-6 pb-8">
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-400/60 mb-2">Unified Search</p>
        <h1 className="text-3xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit' }}>Busca Full-Text</h1>
        <p className="mt-2 text-sm text-white/35">Encontre compostos, artigos e targets por relevância.</p>
      </div>

      {/* Search bar */}
      <div className="animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
        <form onSubmit={handleSubmit} className="relative">
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-500/[0.08] via-teal-500/[0.05] to-cyan-500/[0.08] border border-white/[0.1] p-1">
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/25" />
                <input
                  className="w-full bg-slate-950/60 backdrop-blur-sm rounded-xl pl-12 pr-4 py-4 text-sm text-white placeholder-white/25 border-0 focus:outline-none focus:ring-0"
                  placeholder="Buscar compostos, artigos, targets..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <select className="bg-slate-950/60 backdrop-blur-sm rounded-xl px-4 py-4 text-sm text-white/60 border-0 focus:outline-none"
                value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="">Todas as fontes</option>
                <option value="compound">Compostos</option>
                <option value="article">Artigos</option>
                <option value="target">Targets</option>
              </select>
              <button type="submit"
                className="px-6 py-4 rounded-xl text-sm font-semibold text-slate-950 bg-gradient-to-r from-emerald-400 to-teal-400 transition-all hover:shadow-lg hover:shadow-emerald-500/20 hover:scale-[1.02] active:scale-[0.98]">
                Buscar
              </button>
            </div>
          </div>
        </form>

        {/* Quick suggestions */}
        {!submittedQuery && (
          <div className="mt-4 flex flex-wrap gap-2 animate-fade-in" style={{ animationDelay: '0.2s' }}>
            <span className="text-xs text-white/25 py-1.5">Sugestões:</span>
            {['aspirin', 'inflammation', 'cyclooxygenase', 'diabetes', 'cancer'].map((s) => (
              <button key={s} onClick={() => { setQuery(s); setSubmittedQuery(s) }}
                className="px-3 py-1.5 rounded-lg text-xs text-white/40 bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] hover:text-white/60 transition-all">
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Results */}
      {submittedQuery && (
        <div className="animate-fade-in">
          {isLoading ? <Loader label="Buscando..." /> : null}
          {error ? <div className="glass-card p-5 border-red-500/20 text-red-300 text-sm">{error.message}</div> : null}
          {!isLoading && !error && (!data?.items?.length ? (
            <EmptyState title="Sem resultados" description={`Nenhum resultado para "${submittedQuery}".`} />
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-white/30">
                <Sparkles size={14} className="text-emerald-400/50" />
                <span>{formatNumber(data.total)} resultados para "<span className="text-white/50">{data.query}</span>"</span>
              </div>

              <div className="space-y-3">
                {data.items.map((item, i) => {
                  const cfg = sourceConfig[item.source] || sourceConfig.compound
                  const Icon = cfg.icon
                  const colorClasses = {
                    emerald: 'bg-emerald-500/10 border-emerald-500/10 text-emerald-400',
                    sky: 'bg-sky-500/10 border-sky-500/10 text-sky-400',
                    violet: 'bg-violet-500/10 border-violet-500/10 text-violet-400',
                  }

                  return (
                    <div key={`${item.source}-${item.id}`} className="glass-card p-5 animate-fade-in-up" style={{ animationDelay: `${i * 0.03}s` }}>
                      <div className="flex items-start gap-4">
                        <div className={`w-9 h-9 rounded-lg border flex items-center justify-center flex-shrink-0 ${colorClasses[cfg.color]}`}>
                          <Icon size={16} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1.5">
                            <Pill className={`${colorClasses[cfg.color]} text-[10px]`}>{cfg.label}</Pill>
                            <span className="text-[10px] text-white/20 font-mono">rank {Number(item.rank || 0).toFixed(3)}</span>
                          </div>
                          <h3 className="text-sm font-semibold text-white/85">{item.label}</h3>
                          <p className="text-xs text-white/30 mt-0.5">{item.detail || '—'}</p>
                          {item.highlight && (
                            <div className="mt-3 rounded-lg bg-white/[0.02] border border-white/[0.04] px-3 py-2 text-xs text-white/35 leading-relaxed"
                              dangerouslySetInnerHTML={{ __html: item.highlight }} />
                          )}
                        </div>
                        {item.source === 'compound' && (
                          <Link to={`/compounds/${item.id}`}
                            className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-white/50 hover:text-emerald-300 hover:bg-emerald-500/10 hover:border-emerald-500/20 transition-all flex-shrink-0">
                            Abrir <ArrowUpRight size={11} />
                          </Link>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
