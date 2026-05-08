import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCompounds } from '../lib/hooks'
import { formatNumber, getPhaseBadgeClass, phaseLabel } from '../lib/utils'
import { PageHeader, Section } from '../components/Shell'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Table from '../components/Table'
import Pill from '../components/Pill'
import Pagination from '../components/Pagination'

export default function CompoundsPage() {
  const [filters, setFilters] = useState({
    q: '',
    min_qed: '',
    min_phase: '',
    lipinski: '',
    sort_by: 'name',
    sort_order: 'asc',
    page: 1,
    size: 20,
  })

  const queryParams = useMemo(() => ({
    ...filters,
    min_qed: filters.min_qed || undefined,
    min_phase: filters.min_phase || undefined,
    lipinski: filters.lipinski === '' ? undefined : filters.lipinski,
  }), [filters])

  const { data, isLoading, error } = useCompounds(queryParams)

  const columns = [
    {
      key: 'name',
      header: 'Composto',
      render: (row) => (
        <div>
          <Link to={`/compounds/${row.chembl_id}`} className="font-medium text-white hover:text-brand-300">
            {row.name || 'Sem nome'}
          </Link>
          <p className="mt-1 text-xs text-slate-400">{row.chembl_id}</p>
        </div>
      ),
    },
    { key: 'molecular_formula', header: 'Fórmula' },
    { key: 'mol_weight', header: 'MW', render: (row) => formatNumber(row.mol_weight, { maximumFractionDigits: 2 }) },
    { key: 'qed', header: 'QED', render: (row) => formatNumber(row.qed, { maximumFractionDigits: 4 }) },
    { key: 'ro5_violations', header: 'Ro5', render: (row) => formatNumber(row.ro5_violations) },
    {
      key: 'max_clinical_phase',
      header: 'Fase',
      render: (row) => (
        <Pill className={getPhaseBadgeClass(row.max_clinical_phase)}>{phaseLabel(row.max_clinical_phase)}</Pill>
      ),
    },
    { key: 'total_indications', header: 'Indicações', render: (row) => formatNumber(row.total_indications) },
    { key: 'total_articles', header: 'Artigos', render: (row) => formatNumber(row.total_articles) },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Compounds"
        title="Compound Explorer"
        description="Essa é a página principal do produto. Ela já conversa diretamente com a rota /compounds da API e usa os filtros que o backend já suporta."
      />

      <Section title="Filtros" description="Esses campos espelham a API atual do repositório.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <input
            className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm"
            placeholder="Buscar por nome..."
            value={filters.q}
            onChange={(e) => setFilters((prev) => ({ ...prev, q: e.target.value, page: 1 }))}
          />
          <input
            className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm"
            placeholder="QED mínimo"
            type="number"
            step="0.1"
            min="0"
            max="1"
            value={filters.min_qed}
            onChange={(e) => setFilters((prev) => ({ ...prev, min_qed: e.target.value, page: 1 }))}
          />
          <select
            className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm"
            value={filters.min_phase}
            onChange={(e) => setFilters((prev) => ({ ...prev, min_phase: e.target.value, page: 1 }))}
          >
            <option value="">Fase clínica mínima</option>
            <option value="1">Phase 1</option>
            <option value="2">Phase 2</option>
            <option value="3">Phase 3</option>
            <option value="4">Approved</option>
          </select>
          <select
            className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm"
            value={filters.lipinski}
            onChange={(e) => setFilters((prev) => ({ ...prev, lipinski: e.target.value, page: 1 }))}
          >
            <option value="">Lipinski: todos</option>
            <option value="true">Somente Lipinski OK</option>
            <option value="false">Somente Lipinski falhando</option>
          </select>
          <select
            className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm"
            value={filters.sort_by}
            onChange={(e) => setFilters((prev) => ({ ...prev, sort_by: e.target.value, page: 1 }))}
          >
            <option value="name">Ordenar por nome</option>
            <option value="qed">Ordenar por QED</option>
            <option value="mol_weight">Ordenar por peso molecular</option>
          </select>
          <select
            className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm"
            value={filters.sort_order}
            onChange={(e) => setFilters((prev) => ({ ...prev, sort_order: e.target.value, page: 1 }))}
          >
            <option value="asc">Ascendente</option>
            <option value="desc">Descendente</option>
          </select>
        </div>
      </Section>

      <Section title="Resultados">
        {isLoading ? <Loader label="Buscando compostos..." /> : null}
        {error ? <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5 text-red-200">{error.message}</div> : null}
        {!isLoading && !error && (!data?.items?.length ? <EmptyState description="Nenhum composto foi retornado com esses filtros." /> : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-400">
              <p>{formatNumber(data.total)} compostos encontrados</p>
              <p>Página {data.page} de {data.pages}</p>
            </div>
            <Table columns={columns} rows={data.items} />
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
