import { useState } from 'react'
import { useTargets } from '../lib/hooks'
import { PageHeader, Section } from '../components/Shell'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Table from '../components/Table'
import Pagination from '../components/Pagination'
import { formatNumber } from '../lib/utils'

export default function TargetsPage() {
  const [filters, setFilters] = useState({ q: '', organism: '', page: 1, size: 20 })
  const { data, isLoading, error } = useTargets({
    q: filters.q || undefined,
    organism: filters.organism || undefined,
    page: filters.page,
    size: filters.size,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Targets"
        title="Targets Explorer"
        description="Uma tela enxuta para navegar por alvos biológicos e entender onde existem mais compostos testados."
      />

      <Section title="Filtros">
        <div className="grid gap-4 md:grid-cols-2">
          <input className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm" placeholder="Buscar por nome do target" value={filters.q} onChange={(e) => setFilters((prev) => ({ ...prev, q: e.target.value, page: 1 }))} />
          <input className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 text-sm" placeholder="Organismo" value={filters.organism} onChange={(e) => setFilters((prev) => ({ ...prev, organism: e.target.value, page: 1 }))} />
        </div>
      </Section>

      <Section title="Resultados">
        {isLoading ? <Loader label="Buscando targets..." /> : null}
        {error ? <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5 text-red-200">{error.message}</div> : null}
        {!isLoading && !error && (!data?.items?.length ? <EmptyState description="Nenhum target foi encontrado." /> : (
          <div className="space-y-4">
            <Table
              columns={[
                { key: 'chembl_id', header: 'ChEMBL ID' },
                { key: 'name', header: 'Nome' },
                { key: 'type', header: 'Tipo' },
                { key: 'organism', header: 'Organismo' },
                { key: 'compounds_tested', header: 'Compostos testados', render: (row) => formatNumber(row.compounds_tested) },
              ]}
              rows={data.items}
            />
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
