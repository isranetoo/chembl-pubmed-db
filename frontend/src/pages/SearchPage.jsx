import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useGlobalSearch } from '../lib/hooks'
import { PageHeader, Section } from '../components/Shell'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Pill from '../components/Pill'
import { formatNumber } from '../lib/utils'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('aspirin inflammation')
  const [source, setSource] = useState('')

  const { data, isLoading, error } = useGlobalSearch({
    q: submittedQuery,
    source: source || undefined,
    size: 20,
    page: 1,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Unified search"
        title="Busca full-text"
        description="A rota /search é um dos ativos mais valiosos da API. Vale dar destaque visual para ela no produto, porque ela transforma o banco em ferramenta de descoberta."
      />

      <Section title="Buscar">
        <form
          className="flex flex-col gap-4 md:flex-row"
          onSubmit={(e) => {
            e.preventDefault()
            if (query.trim()) setSubmittedQuery(query.trim())
          }}
        >
          <input
            className="flex-1 rounded-2xl border border-white/10 bg-slate-900 px-5 py-4 text-sm"
            placeholder="Ex: aspirin inflammation"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select className="rounded-2xl border border-white/10 bg-slate-900 px-4 py-4 text-sm" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">Todas as fontes</option>
            <option value="compound">Somente compounds</option>
            <option value="article">Somente articles</option>
            <option value="target">Somente targets</option>
          </select>
          <button className="rounded-2xl bg-brand-500 px-5 py-4 text-sm font-medium text-slate-950 hover:bg-brand-400">Buscar</button>
        </form>
      </Section>

      <Section title="Resultados">
        {isLoading ? <Loader label="Executando busca..." /> : null}
        {error ? <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5 text-red-200">{error.message}</div> : null}
        {!isLoading && !error && (!data?.items?.length ? <EmptyState description="Nenhum resultado encontrado para essa consulta." /> : (
          <div className="space-y-4">
            <p className="text-sm text-slate-400">{formatNumber(data.total)} resultados para “{data.query}”</p>
            {data.items.map((item) => (
              <div key={`${item.source}-${item.id}`} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="mb-2 flex flex-wrap gap-2">
                      <Pill className="border-white/10 bg-white/5 text-slate-300">{item.source}</Pill>
                      <Pill className="border-brand-400/20 bg-brand-500/10 text-brand-200">rank {Number(item.rank || 0).toFixed(3)}</Pill>
                    </div>
                    <h3 className="text-lg font-medium text-white">{item.label}</h3>
                    <p className="mt-1 text-sm text-slate-400">{item.detail || 'Sem detalhe adicional'}</p>
                  </div>
                  {item.source === 'compound' ? (
                    <Link to={`/compounds/${item.id}`} className="rounded-xl border border-white/10 px-3 py-2 text-sm text-white hover:bg-white/5">Abrir composto</Link>
                  ) : null}
                </div>
                {item.highlight ? (
                  <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-slate-300" dangerouslySetInnerHTML={{ __html: item.highlight }} />
                ) : null}
              </div>
            ))}
          </div>
        ))}
      </Section>
    </div>
  )
}
