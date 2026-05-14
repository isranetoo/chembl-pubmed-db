import { useState } from 'react'
import { useArticles } from '../lib/hooks'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Pill from '../components/Pill'
import Pagination from '../components/Pagination'
import Section from '../components/Section'
import { formatNumber } from '../lib/utils'
import { ExternalLink, Calendar, BookOpen } from 'lucide-react'

export default function ArticlesPage() {
  const [filters, setFilters] = useState({
    q: '', journal: '', min_year: '', max_year: '',
    only_abstract: true, pub_type: '', page: 1, size: 12,
  })

  const { data, isLoading, error } = useArticles({
    ...filters,
    min_year: filters.min_year || undefined,
    max_year: filters.max_year || undefined,
    journal: filters.journal || undefined,
    q: filters.q || undefined,
    pub_type: filters.pub_type || undefined,
  })

  return (
    <div className="space-y-6 pb-8">
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-sky-400/60 mb-2">Literature</p>
        <h1 className="text-3xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit' }}>Articles Explorer</h1>
        <p className="mt-2 text-sm text-white/35">Explore a literatura científica do PubMed associada aos compostos.</p>
      </div>

      <Section title="Filtros" delay={0.05}>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <input className="glass-input" placeholder="Buscar no título/abstract" value={filters.q}
            onChange={(e) => setFilters(p => ({ ...p, q: e.target.value, page: 1 }))} />
          <input className="glass-input" placeholder="Journal" value={filters.journal}
            onChange={(e) => setFilters(p => ({ ...p, journal: e.target.value, page: 1 }))} />
          <input className="glass-input" placeholder="Tipo de publicação" value={filters.pub_type}
            onChange={(e) => setFilters(p => ({ ...p, pub_type: e.target.value, page: 1 }))} />
          <input className="glass-input" placeholder="Ano mínimo" type="number" value={filters.min_year}
            onChange={(e) => setFilters(p => ({ ...p, min_year: e.target.value, page: 1 }))} />
          <input className="glass-input" placeholder="Ano máximo" type="number" value={filters.max_year}
            onChange={(e) => setFilters(p => ({ ...p, max_year: e.target.value, page: 1 }))} />
          <label className="glass-input flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={filters.only_abstract}
              onChange={(e) => setFilters(p => ({ ...p, only_abstract: e.target.checked, page: 1 }))}
              className="w-4 h-4 rounded border-white/20 bg-white/5 text-emerald-500 focus:ring-emerald-500/30" />
            <span className="text-white/50 text-sm">Somente com abstract</span>
          </label>
        </div>
      </Section>

      <div className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        {isLoading ? <Loader label="Buscando artigos..." /> : null}
        {error ? <div className="glass-card p-5 border-red-500/20 text-red-300 text-sm">{error.message}</div> : null}
        {!isLoading && !error && (!data?.items?.length ? <EmptyState /> : (
          <div className="space-y-4">
            <p className="text-sm text-white/30">{formatNumber(data.total)} artigos encontrados</p>

            <div className="space-y-3">
              {data.items.map((a, i) => (
                <article key={a.pmid} className="glass-card p-5 animate-fade-in-up" style={{ animationDelay: `${i * 0.03}s` }}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start gap-3">
                        <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <BookOpen size={16} className="text-sky-400" />
                        </div>
                        <div>
                          <h3 className="text-sm font-semibold text-white/85 leading-snug">{a.title || 'Sem título'}</h3>
                          <div className="flex items-center gap-2 mt-1.5 text-xs text-white/30">
                            <span>{a.journal || '—'}</span>
                            {a.pub_year && (
                              <>
                                <span className="w-1 h-1 rounded-full bg-white/15" />
                                <span className="flex items-center gap-1"><Calendar size={10} />{a.pub_year}</span>
                              </>
                            )}
                            <span className="w-1 h-1 rounded-full bg-white/15" />
                            <span className="font-mono">PMID {a.pmid}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <a href={`https://pubmed.ncbi.nlm.nih.gov/${a.pmid}/`} target="_blank" rel="noreferrer"
                      className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-white/50 hover:text-white/80 hover:bg-white/[0.06] transition-all flex-shrink-0">
                      PubMed <ExternalLink size={11} />
                    </a>
                  </div>
                  {Array.isArray(a.pub_types) && a.pub_types.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5 ml-12">
                      {a.pub_types.slice(0, 3).map((t) => (
                        <Pill key={t} className="bg-white/[0.04] border-white/[0.08] text-white/40">{t}</Pill>
                      ))}
                    </div>
                  )}
                  {a.abstract_snippet && (
                    <p className="mt-3 ml-12 text-xs text-white/30 leading-relaxed line-clamp-2">{a.abstract_snippet}...</p>
                  )}
                  {a.compounds && (
                    <p className="mt-2 ml-12 text-[11px] text-emerald-400/40">Compostos: {a.compounds}</p>
                  )}
                </article>
              ))}
            </div>

            <Pagination page={data.page} pages={data.pages}
              onPrevious={() => setFilters(p => ({ ...p, page: Math.max(1, p.page - 1) }))}
              onNext={() => setFilters(p => ({ ...p, page: Math.min(data.pages, p.page + 1) }))} />
          </div>
        ))}
      </div>
    </div>
  )
}
