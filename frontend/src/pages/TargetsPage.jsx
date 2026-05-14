import { useState } from 'react'
import { useTargets } from '../lib/hooks'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Table from '../components/Table'
import Pagination from '../components/Pagination'
import Section from '../components/Section'
import { formatNumber } from '../lib/utils'
import { Crosshair } from 'lucide-react'

export default function TargetsPage() {
  const [filters, setFilters] = useState({ q: '', organism: '', page: 1, size: 20 })
  const { data, isLoading, error } = useTargets({
    q: filters.q || undefined,
    organism: filters.organism || undefined,
    page: filters.page,
    size: filters.size,
  })

  return (
    <div className="space-y-6 pb-8">
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-violet-400/60 mb-2">Targets</p>
        <h1 className="text-3xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit' }}>Targets Explorer</h1>
        <p className="mt-2 text-sm text-white/35">Navegue por alvos biológicos e veja quantos compostos foram testados.</p>
      </div>

      <Section title="Filtros" delay={0.05}>
        <div className="grid gap-3 sm:grid-cols-2">
          <input className="glass-input" placeholder="Nome do target" value={filters.q}
            onChange={(e) => setFilters(p => ({ ...p, q: e.target.value, page: 1 }))} />
          <input className="glass-input" placeholder="Organismo" value={filters.organism}
            onChange={(e) => setFilters(p => ({ ...p, organism: e.target.value, page: 1 }))} />
        </div>
      </Section>

      <div className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        {isLoading ? <Loader label="Buscando targets..." /> : null}
        {error ? <div className="glass-card p-5 border-red-500/20 text-red-300 text-sm">{error.message}</div> : null}
        {!isLoading && !error && (!data?.items?.length ? <EmptyState /> : (
          <div className="space-y-4">
            <p className="text-sm text-white/30">{formatNumber(data.total)} targets</p>
            <Table columns={[
              { key: 'chembl_id', header: 'ID', render: (r) => <code className="text-[11px] text-emerald-300/50 font-mono">{r.chembl_id}</code> },
              { key: 'name', header: 'Nome', render: (r) => (
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-violet-500/10 border border-violet-500/10 flex items-center justify-center flex-shrink-0">
                    <Crosshair size={13} className="text-violet-400" />
                  </div>
                  <span className="text-white/80 font-medium text-sm">{r.name}</span>
                </div>
              )},
              { key: 'type', header: 'Tipo', render: (r) => <span className="text-white/40 text-xs">{r.type || '—'}</span> },
              { key: 'organism', header: 'Organismo', render: (r) => <span className="text-white/40 text-xs italic">{r.organism || '—'}</span> },
              { key: 'compounds_tested', header: 'Compostos', render: (r) => (
                <div className="flex items-center gap-2">
                  <div className="w-12 h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-400"
                      style={{ width: `${Math.min((r.compounds_tested / 10) * 100, 100)}%` }} />
                  </div>
                  <span className="text-xs text-white/50">{formatNumber(r.compounds_tested)}</span>
                </div>
              )},
            ]} rows={data.items} />
            <Pagination page={data.page} pages={data.pages}
              onPrevious={() => setFilters(p => ({ ...p, page: Math.max(1, p.page - 1) }))}
              onNext={() => setFilters(p => ({ ...p, page: Math.min(data.pages, p.page + 1) }))} />
          </div>
        ))}
      </div>
    </div>
  )
}
