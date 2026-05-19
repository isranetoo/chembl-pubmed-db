import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCompounds } from '../lib/hooks'
import { formatNumber, getPhaseBadgeClass, phaseLabel } from '../lib/utils'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Table from '../components/Table'
import Pill from '../components/Pill'
import Pagination from '../components/Pagination'
import Section from '../components/Section'
import { FlaskConical, SlidersHorizontal, ArrowUpRight } from 'lucide-react'

export default function CompoundsPage() {
  const [filters, setFilters] = useState({
    q: '', min_qed: '', min_phase: '', lipinski: '',
    sort_by: 'name', sort_order: 'asc', page: 1, size: 20,
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
      key: 'name', header: 'Composto',
      render: (row) => (
        <Link to={`/compounds/${row.chembl_id}`} className="group flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-600 to-green-900 flex items-center justify-center flex-shrink-0 shadow-sm">
            <FlaskConical size={14} className="text-white" />
          </div>
          <div>
            <p className="font-medium text-gray-800 group-hover:text-green-700 transition-colors flex items-center gap-1">
              {row.name || 'Sem nome'}
              <ArrowUpRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity text-green-700" />
            </p>
            <p className="text-[11px] text-gray-500 font-mono">{row.chembl_id}</p>
          </div>
        </Link>
      ),
    },
    { key: 'molecular_formula', header: 'Fórmula' },
    { key: 'mol_weight', header: 'MW', render: (row) => formatNumber(row.mol_weight, { maximumFractionDigits: 2 }) },
    { key: 'qed', header: 'QED', render: (row) => (
      <div className="flex items-center gap-2">
        <div className="w-16 h-1.5 rounded-full bg-gray-100 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-green-600 to-green-900" style={{ width: `${(row.qed || 0) * 100}%` }} />
        </div>
        <span className="text-xs text-gray-600">{formatNumber(row.qed, { maximumFractionDigits: 3 })}</span>
      </div>
    )},
    {
      key: 'max_clinical_phase', header: 'Fase',
      render: (row) => <Pill className={getPhaseBadgeClass(row.max_clinical_phase)}>{phaseLabel(row.max_clinical_phase)}</Pill>,
    },
    { key: 'total_indications', header: 'Ind.', render: (row) => <span className="text-gray-600">{formatNumber(row.total_indications)}</span> },
    { key: 'total_articles', header: 'Art.', render: (row) => <span className="text-gray-600">{formatNumber(row.total_articles)}</span> },
  ]

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-green-700 mb-2">Compounds</p>
        <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-gray-800">
          <span className="bg-gradient-to-br from-green-600 to-green-900 text-transparent bg-clip-text">Compound</span> Explorer
        </h1>
        <p className="mt-2 text-sm text-neutral-600">Navegue, filtre e descubra compostos farmacológicos do ChEMBL.</p>
      </div>

      {/* Filters */}
      <Section title="Filtros" delay={0.05}>
        <div className="flex items-center gap-2 mb-4 text-gray-500">
          <SlidersHorizontal size={14} />
          <span className="text-xs">Refine sua busca</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <input className="glass-input" placeholder="Buscar por nome..."
            value={filters.q} onChange={(e) => setFilters(p => ({ ...p, q: e.target.value, page: 1 }))} />
          <input className="glass-input" placeholder="QED mínimo" type="number" step="0.1" min="0" max="1"
            value={filters.min_qed} onChange={(e) => setFilters(p => ({ ...p, min_qed: e.target.value, page: 1 }))} />
          <select className="glass-input" value={filters.min_phase}
            onChange={(e) => setFilters(p => ({ ...p, min_phase: e.target.value, page: 1 }))}>
            <option value="">Fase clínica</option>
            <option value="1">Phase 1+</option>
            <option value="2">Phase 2+</option>
            <option value="3">Phase 3+</option>
            <option value="4">Approved</option>
          </select>
          <select className="glass-input" value={filters.lipinski}
            onChange={(e) => setFilters(p => ({ ...p, lipinski: e.target.value, page: 1 }))}>
            <option value="">Lipinski: todos</option>
            <option value="true">Lipinski OK</option>
            <option value="false">Lipinski fail</option>
          </select>
        </div>
        <div className="flex gap-3 mt-3">
          <select className="glass-input w-auto" value={filters.sort_by}
            onChange={(e) => setFilters(p => ({ ...p, sort_by: e.target.value, page: 1 }))}>
            <option value="name">Ordenar: Nome</option>
            <option value="qed">Ordenar: QED</option>
            <option value="mol_weight">Ordenar: MW</option>
          </select>
          <select className="glass-input w-auto" value={filters.sort_order}
            onChange={(e) => setFilters(p => ({ ...p, sort_order: e.target.value, page: 1 }))}>
            <option value="asc">↑ Asc</option>
            <option value="desc">↓ Desc</option>
          </select>
        </div>
      </Section>

      {/* Results */}
      <div className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        {isLoading ? <Loader label="Buscando compostos..." /> : null}
        {error ? <div className="bg-white border border-rose-300 rounded-xl p-5 text-rose-700 text-sm">{error.message}</div> : null}
        {!isLoading && !error && (!data?.items?.length ? <EmptyState /> : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm text-neutral-500">
              <p>{formatNumber(data.total)} compostos</p>
              <p>Página {data.page}/{data.pages}</p>
            </div>
            <Table columns={columns} rows={data.items} />
            <Pagination page={data.page} pages={data.pages}
              onPrevious={() => setFilters(p => ({ ...p, page: Math.max(1, p.page - 1) }))}
              onNext={() => setFilters(p => ({ ...p, page: Math.min(data.pages, p.page + 1) }))} />
          </div>
        ))}
      </div>
    </div>
  )
}
