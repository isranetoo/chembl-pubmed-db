import { useState } from 'react'
import { useArticles } from '../lib/hooks'
import { PageHeader, Section } from '../components/Shell'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Pill from '../components/Pill'
import Pagination from '../components/Pagination'
import { formatNumber } from '../lib/utils'

export default function ArticlesPage() {
  const [filters, setFilters] = useState({
    q: '',
    journal: '',
    min_year: '',
    max_year: '',
    only_abstract: true,
    pub_type: '',
    page: 1,
    size: 12,
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
    <div className="space-y-6">
      <PageHeader
        eyebrow="Literature"
        title="Articles Explorer"
        description="Essa tela usa cards porque título, journal e snippet do abstract precisam de leitura confortável."
      />

      <Section title="Filtros">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <input className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm" placeholder="Buscar no título/abstract" value={filters.q} onChange={(e) => setFilters((prev) => ({ ...prev, q: e.target.value, page: 1 }))} />
          <input className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm" placeholder="Journal" value={filters.journal} onChange={(e) => setFilters((prev) => ({ ...prev, journal: e.target.value, page: 1 }))} />
          <input className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm" placeholder="Ano mínimo" type="number" value={filters.min_year} onChange={(e) => setFilters((prev) => ({ ...prev, min_year: e.target.value, page: 1 }))} />
          <input className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm" placeholder="Ano máximo" type="number" value={filters.max_year} onChange={(e) => setFilters((prev) => ({ ...prev, max_year: e.target.value, page: 1 }))} />
          <input className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm" placeholder="Publication type" value={filters.pub_type} onChange={(e) => setFilters((prev) => ({ ...prev, pub_type: e.target.value, page: 1 }))} />
          <label className="flex items-center gap-3 rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-slate-300">
            <input type="checkbox" checked={filters.only_abstract} onChange={(e) => setFilters((prev) => ({ ...prev, only_abstract: e.target.checked, page: 1 }))} />
            Somente artigos com abstract
          </label>
        </div>
      </Section>

      <Section title="Resultados">
        {isLoading ? <Loader label="Buscando artigos..." /> : null}
        {error ? <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5 text-red-200">{error.message}</div> : null}
        {!isLoading && !error && (!data?.items?.length ? <EmptyState description="Nenhum artigo retornado com os filtros atuais." /> : (
          <div className="space-y-4">
            <p className="text-sm text-slate-400">{formatNumber(data.total)} artigos encontrados</p>
            {data.items.map((article) => (
              <article key={article.pmid} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-medium text-white">{article.title}</h3>
                    <p className="mt-2 text-sm text-slate-400">{article.journal || 'Journal não informado'} • {article.pub_year || 'Ano não informado'} • PMID {article.pmid}</p>
                  </div>
                  <a href={`https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/`} target="_blank" rel="noreferrer" className="rounded-xl border border-white/10 px-3 py-2 text-sm text-white hover:bg-white/5">PubMed</a>
                </div>
                {Array.isArray(article.pub_types) && article.pub_types.length ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {article.pub_types.slice(0, 4).map((type) => (
                      <Pill key={type} className="border-white/10 bg-white/5 text-slate-300">{type}</Pill>
                    ))}
                  </div>
                ) : null}
                {article.abstract_snippet ? <p className="mt-4 text-sm leading-6 text-slate-300">{article.abstract_snippet}...</p> : null}
                {article.compounds ? <p className="mt-4 text-xs text-slate-500">Compostos relacionados: {article.compounds}</p> : null}
              </article>
            ))}
            <Pagination
              page={data.page}
              pages={data.pages}
              onPrevious={() => setFilters((prev) => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
              onNext={() => setFilters((prev) => ({ ...prev, page: Math.min(data.pages, prev.page + 1) }))}
            />
          </div>
        ))}
      </Section>
    </div>
  )
}
