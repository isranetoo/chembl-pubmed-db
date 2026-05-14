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
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500/20 to-teal-500/10 border border-emerald-500/10 flex items-center justify-center flex-shrink-0">
            <FlaskConical size={14} className="text-emerald-400" />
          </div>
          <div>
            <p className="font-medium text-white/90 group-hover:text-emerald-300 transition-colors flex items-center gap-1">
              {row.name || 'Sem nome'}
              <ArrowUpRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity text-emerald-400" />
            </p>
            <p className="text-[11px] text-white/30 font-mono">{row.chembl_id}</p>
          </div>
        </Link>
      ),
    },
    { key: 'molecular_formula', header: 'Fórmula' },
    { key: 'mol_weight', header: 'MW', render: (row) => formatNumber(row.mol_weight, { maximumFractionDigits: 2 }) },
    { key: 'qed', header: 'QED', render: (row) => (
      <div className="flex items-center gap-2">
        <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400" style={{ width: `${(row.qed || 0) * 100}%` }} />
        </div>
        <span className="text-xs text-white/50">{formatNumber(row.qed, { maximumFractionDigits: 3 })}</span>
      </div>
    )},
    {
      key: 'max_clinical_phase', header: 'Fase',
      render: (row) => <Pill className={getPhaseBadgeClass(row.max_clinical_phase)}>{phaseLabel(row.max_clinical_phase)}</Pill>,
    },
    { key: 'total_indications', header: 'Ind.', render: (row) => <span className="text-white/50">{formatNumber(row.total_indications)}</span> },
    { key: 'total_articles', header: 'Art.', render: (row) => <span className="text-white/50">{formatNumber(row.total_articles)}</span> },
  ]

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-400/60 mb-2">Compounds</p>
        <h1 className="text-3xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit' }}>Compound Explorer</h1>
        <p className="mt-2 text-sm text-white/35">Navegue, filtre e descubra compostos farmacológicos do ChEMBL.</p>
      </div>

      {/* Filters */}
      <Section title="Filtros" delay={0.05}>
        <div className="flex items-center gap-2 mb-4 text-white/40">
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
        {error ? <div className="glass-card p-5 border-red-500/20 text-red-300 text-sm">{error.message}</div> : null}
        {!isLoading && !error && (!data?.items?.length ? <EmptyState /> : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm text-white/35">
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
