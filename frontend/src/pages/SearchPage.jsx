import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useGlobalSearch } from '../lib/hooks'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Pill from '../components/Pill'
import { formatNumber } from '../lib/utils'
import { Search, ArrowUpRight, FlaskConical, BookOpen, Crosshair, Sparkles } from 'lucide-react'

const sourceConfig = {
  compound: { icon: FlaskConical, color: 'emerald', label: 'Composto' },
  article:  { icon: BookOpen,     color: 'sky',     label: 'Artigo' },
  target:   { icon: Crosshair,    color: 'violet',  label: 'Target' },
}

const colorClasses = {
  emerald: 'bg-green-100 border-green-200 text-green-700',
  sky:     'bg-sky-100 border-sky-200 text-sky-700',
  violet:  'bg-violet-100 border-violet-200 text-violet-700',
}

const pillClasses = {
  emerald: 'bg-green-100 border-green-300 text-green-800',
  sky:     'bg-sky-100 border-sky-300 text-sky-800',
  violet:  'bg-violet-100 border-violet-300 text-violet-800',
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
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-700 mb-2">Unified Search</p>
        <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-gray-800">
          Busca <span className="bg-gradient-to-br from-green-600 to-green-900 text-transparent bg-clip-text">Full-Text</span>
        </h1>
        <p className="mt-2 text-sm text-neutral-600">Encontre compostos, artigos e targets por relevância.</p>
      </div>

      {/* Search bar */}
      <div className="animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
        <form onSubmit={handleSubmit} className="relative">
          <div className="relative overflow-hidden rounded-2xl bg-white border border-gray-200 shadow-card p-1">
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  className="w-full bg-white rounded-xl pl-12 pr-4 py-4 text-sm text-gray-800 placeholder-gray-400 border-0 focus:outline-none focus:ring-0"
                  placeholder="Buscar compostos, artigos, targets..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <select
                className="bg-gray-50 rounded-xl px-4 py-4 text-sm text-gray-700 border border-gray-200 focus:outline-none focus:border-[#5c8d2f]"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                <option value="">Todas as fontes</option>
                <option value="compound">Compostos</option>
                <option value="article">Artigos</option>
                <option value="target">Targets</option>
              </select>
              <button
                type="submit"
                className="px-6 py-4 rounded-xl text-sm font-semibold text-white bg-gradient-to-br from-green-600 to-green-900 shadow-md transition-all hover:shadow-xl hover:scale-[1.03] active:scale-[0.98]"
              >
                Buscar
              </button>
            </div>
          </div>
        </form>

        {/* Quick suggestions */}
        {!submittedQuery && (
          <div className="mt-4 flex flex-wrap gap-2 animate-fade-in" style={{ animationDelay: '0.2s' }}>
            <span className="text-xs text-gray-500 py-1.5">Sugestões:</span>
            {['aspirin', 'inflammation', 'cyclooxygenase', 'diabetes', 'cancer'].map((s) => (
              <button
                key={s}
                onClick={() => { setQuery(s); setSubmittedQuery(s) }}
                className="px-3 py-1.5 rounded-lg text-xs text-gray-700 bg-white border border-gray-200 hover:bg-green-50 hover:text-green-800 hover:border-[#5c8d2f] transition-all"
              >
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
          {error ? <div className="bg-white border border-rose-300 rounded-xl p-5 text-rose-700 text-sm">{error.message}</div> : null}
          {!isLoading && !error && (!data?.items?.length ? (
            <EmptyState title="Sem resultados" description={`Nenhum resultado para "${submittedQuery}".`} />
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-neutral-500">
                <Sparkles size={14} className="text-green-700" />
                <span>{formatNumber(data.total)} resultados para "<span className="text-gray-800 font-medium">{data.query}</span>"</span>
              </div>

              <div className="space-y-3">
                {data.items.map((item, i) => {
                  const cfg = sourceConfig[item.source] || sourceConfig.compound
                  const Icon = cfg.icon

                  return (
                    <div
                      key={`${item.source}-${item.id}`}
                      className="bg-white border border-gray-200 rounded-xl shadow-card p-5 animate-fade-in-up transition-all duration-300 hover:shadow-elevated hover:-translate-y-0.5"
                      style={{ animationDelay: `${i * 0.03}s` }}
                    >
                      <div className="flex items-start gap-4">
                        <div className={`w-9 h-9 rounded-lg border flex items-center justify-center flex-shrink-0 ${colorClasses[cfg.color]}`}>
                          <Icon size={16} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1.5">
                            <Pill className={`${pillClasses[cfg.color]} text-[10px]`}>{cfg.label}</Pill>
                            <span className="text-[10px] text-gray-400 font-mono">rank {Number(item.rank || 0).toFixed(3)}</span>
                          </div>
                          <h3 className="text-sm font-semibold text-gray-800">{item.label}</h3>
                          <p className="text-xs text-neutral-500 mt-0.5">{item.detail || '—'}</p>
                          {item.highlight && (
                            <div
                              className="mt-3 rounded-lg bg-gray-50 border border-gray-200 px-3 py-2 text-xs text-gray-700 leading-relaxed"
                              dangerouslySetInnerHTML={{ __html: item.highlight }}
                            />
                          )}
                        </div>
                        {item.source === 'compound' && (
                          <Link
                            to={`/compounds/${item.id}`}
                            className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 hover:text-green-700 hover:bg-green-50 hover:border-[#5c8d2f] transition-all flex-shrink-0"
                          >
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
