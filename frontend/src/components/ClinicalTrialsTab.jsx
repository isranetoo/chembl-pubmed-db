import { useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertCircle, Building2, CheckCircle2, ChevronRight,
  ExternalLink, FlaskConical, RefreshCw, TestTube, Users,
} from 'lucide-react'
import { useCompoundTrials, useSyncCompoundTrials } from '../lib/hooks'
import EmptyState from './EmptyState'
import Pagination from './Pagination'

const PAGE_SIZE = 10

// Status badge palette tuned for the light theme.
const STATUS_STYLES = {
  RECRUITING:              'bg-green-100 text-green-800 border-green-300',
  ACTIVE_NOT_RECRUITING:   'bg-sky-100 text-sky-800 border-sky-300',
  ENROLLING_BY_INVITATION: 'bg-sky-100 text-sky-800 border-sky-300',
  COMPLETED:               'bg-gray-100 text-gray-700 border-gray-300',
  TERMINATED:              'bg-rose-100 text-rose-800 border-rose-300',
  WITHDRAWN:               'bg-rose-100 text-rose-800 border-rose-300',
  SUSPENDED:               'bg-amber-100 text-amber-800 border-amber-300',
  NOT_YET_RECRUITING:      'bg-violet-100 text-violet-800 border-violet-300',
}

const PHASE_OPTIONS = ['PHASE1', 'PHASE2', 'PHASE3', 'PHASE4']
const STATUS_OPTIONS = ['RECRUITING', 'ACTIVE_NOT_RECRUITING', 'COMPLETED', 'TERMINATED']

function statusClass(s) {
  return STATUS_STYLES[s] || 'bg-gray-100 text-gray-600 border-gray-200'
}

function fmtDate(s) {
  if (!s) return '—'
  return s.slice(0, 10)
}

// ── KPI strip ────────────────────────────────────────────────────────

function KpiCard({ label, value, accent, icon: Icon }) {
  return (
    <div className={`relative overflow-hidden rounded-2xl bg-white border-t-4 ${accent} border-x border-b border-gray-200 p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md`}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">{label}</p>
        <Icon size={14} className="text-gray-400" />
      </div>
      <p className="text-2xl font-bold text-gray-800">{value ?? 0}</p>
    </div>
  )
}

// ── Trial card ───────────────────────────────────────────────────────

function TrialCard({ trial }) {
  return (
    <a
      href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
      target="_blank"
      rel="noreferrer"
      className="group block rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-[#5c8d2f] hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <code className="text-[10px] font-mono text-green-700">{trial.nct_id}</code>
          <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium border ${statusClass(trial.status)}`}>
            {trial.status || '—'}
          </span>
          {(trial.phases || []).map((p) => (
            <span key={p} className="rounded-md px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200">
              {p.replace('PHASE', 'Fase ')}
            </span>
          ))}
        </div>
        <ChevronRight size={14} className="text-gray-400 group-hover:text-green-700 transition-colors flex-shrink-0 mt-0.5" />
      </div>

      <h3 className="text-sm font-medium text-gray-800 leading-snug line-clamp-2 mb-2">{trial.title || 'Sem título'}</h3>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-x-3 gap-y-1.5 text-[11px] text-neutral-500">
        {trial.sponsor && (
          <div className="flex items-center gap-1.5 truncate">
            <Building2 size={11} className="flex-shrink-0" />
            <span className="truncate">{trial.sponsor}</span>
          </div>
        )}
        {trial.enrollment != null && (
          <div className="flex items-center gap-1.5">
            <Users size={11} className="flex-shrink-0" />
            <span>{trial.enrollment.toLocaleString()} pacientes</span>
          </div>
        )}
        {trial.locations_count != null && (
          <div className="flex items-center gap-1.5">
            <TestTube size={11} className="flex-shrink-0" />
            <span>{trial.locations_count} sites</span>
          </div>
        )}
        {trial.start_date && (
          <div className="flex items-center gap-1.5">
            <Activity size={11} className="flex-shrink-0" />
            <span>Início {fmtDate(trial.start_date)}</span>
          </div>
        )}
      </div>

      {trial.primary_endpoint && (
        <p className="mt-2.5 text-[11px] text-neutral-500 leading-relaxed line-clamp-2">
          <span className="text-gray-700 font-medium">Endpoint:</span> {trial.primary_endpoint}
        </p>
      )}
    </a>
  )
}

// ── Subcomponents ────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 animate-pulse">
      <div className="flex items-center gap-2 mb-3">
        <div className="h-3 w-20 rounded bg-gray-200" />
        <div className="h-4 w-16 rounded bg-gray-200" />
      </div>
      <div className="h-3 w-full rounded bg-gray-200 mb-2" />
      <div className="h-3 w-3/4 rounded bg-gray-200 mb-3" />
      <div className="grid grid-cols-4 gap-2">
        <div className="h-2.5 rounded bg-gray-100" />
        <div className="h-2.5 rounded bg-gray-100" />
        <div className="h-2.5 rounded bg-gray-100" />
        <div className="h-2.5 rounded bg-gray-100" />
      </div>
    </div>
  )
}

function ErrorCard({ message, onRetry }) {
  return (
    <div className="rounded-2xl border border-rose-300 bg-rose-50 p-6 text-center">
      <AlertCircle size={20} className="text-rose-600 mx-auto mb-2" />
      <p className="text-sm text-rose-700 mb-3">{message}</p>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs text-rose-700 hover:bg-rose-100 transition-colors"
      >
        <RefreshCw size={12} /> Tentar de novo
      </button>
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────

export default function ClinicalTrialsTab({ chemblId, drugName }) {
  const [phaseFilter, setPhaseFilter] = useState(null)
  const [statusFilter, setStatusFilter] = useState(null)
  const [page, setPage] = useState(1)

  // Trocar filtro reseta pra página 1 — senão fica numa página vazia.
  useEffect(() => { setPage(1) }, [phaseFilter, statusFilter])

  const params = useMemo(() => {
    const p = { page, size: PAGE_SIZE }
    if (phaseFilter) p.phase = phaseFilter
    if (statusFilter) p.status = statusFilter
    return p
  }, [phaseFilter, statusFilter, page])

  const trialsQ = useCompoundTrials(chemblId, params)
  const syncMut = useSyncCompoundTrials(chemblId)

  const data = trialsQ.data
  const kpis = data?.kpis || {}
  const items = data?.items || []
  const pages = data?.pages || 0
  const total = data?.total || 0
  const isSyncing = syncMut.isPending
  const isLoading = trialsQ.isLoading

  const handleSync = () => syncMut.mutate(drugName)

  if (trialsQ.error && !isLoading) {
    return <ErrorCard message={trialsQ.error.message} onRetry={() => trialsQ.refetch()} />
  }

  return (
    <div className="space-y-4 animate-fade-in">
      {/* KPI strip */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Total"      value={kpis.total_trials}      accent="border-cyan-500"   icon={FlaskConical} />
        <KpiCard label="Recrutando" value={kpis.recruiting_trials} accent="border-[#5c8d2f]" icon={Activity} />
        <KpiCard label="Fase 3"     value={kpis.phase3_trials}     accent="border-violet-500" icon={TestTube} />
        <KpiCard label="Fase 4"     value={kpis.phase4_trials}     accent="border-amber-500"  icon={CheckCircle2} />
      </div>

      {/* Action bar */}
      <div className="flex flex-wrap items-center gap-2 p-3 rounded-xl bg-gray-50 border border-gray-200">
        <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mr-1">Fase:</span>
        {PHASE_OPTIONS.map((p) => (
          <button
            key={p}
            onClick={() => setPhaseFilter(phaseFilter === p ? null : p)}
            className={`rounded-md border px-2 py-1 text-[11px] font-medium transition-colors ${
              phaseFilter === p
                ? 'bg-violet-100 text-violet-800 border-violet-300'
                : 'bg-white text-gray-600 border-gray-200 hover:text-violet-700 hover:border-violet-300'
            }`}
          >
            {p.replace('PHASE', 'Fase ')}
          </button>
        ))}
        <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold ml-3 mr-1">Status:</span>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(statusFilter === s ? null : s)}
            className={`rounded-md border px-2 py-1 text-[11px] font-medium transition-colors ${
              statusFilter === s
                ? 'bg-green-100 text-green-800 border-green-300'
                : 'bg-white text-gray-600 border-gray-200 hover:text-green-700 hover:border-green-300'
            }`}
          >
            {s.replace(/_/g, ' ')}
          </button>
        ))}

        <div className="ml-auto flex items-center gap-2">
          {syncMut.error && (
            <span className="text-[11px] text-rose-600">{syncMut.error.message}</span>
          )}
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="inline-flex items-center gap-1.5 rounded-lg text-xs font-semibold text-white bg-gradient-to-br from-green-600 to-green-900 px-3 py-1.5 shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw size={12} className={isSyncing ? 'animate-spin' : ''} />
            {isSyncing ? 'Sincronizando...' : 'Atualizar da CT.gov'}
          </button>
        </div>
      </div>

      {/* List / states */}
      {isLoading ? (
        <div className="space-y-3">
          <SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
      ) : kpis.total_trials === 0 ? (
        <div className="rounded-2xl bg-white border border-gray-200 shadow-card p-12 text-center animate-fade-in">
          <div className="w-14 h-14 rounded-2xl bg-green-50 border border-green-200 flex items-center justify-center mx-auto mb-4">
            <FlaskConical size={24} className="text-green-700" />
          </div>
          <h3 className="text-base font-semibold text-gray-800 mb-1">
            Nenhum ensaio cacheado ainda
          </h3>
          <p className="text-sm text-neutral-500 mb-5">
            Busque na ClinicalTrials.gov pelo nome do composto.
          </p>
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="inline-flex items-center gap-1.5 rounded-lg text-sm font-semibold text-white bg-gradient-to-br from-green-600 to-green-900 px-4 py-2 shadow-md hover:shadow-lg hover:scale-[1.02] transition-all disabled:opacity-50"
          >
            <RefreshCw size={13} className={isSyncing ? 'animate-spin' : ''} />
            {isSyncing ? 'Buscando...' : 'Buscar trials agora'}
          </button>
        </div>
      ) : items.length === 0 ? (
        <EmptyState description="Nenhum trial bate com os filtros." />
      ) : (
        <>
          <div className="flex items-center justify-between px-1 text-[11px] text-neutral-500">
            <span>
              Mostrando {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} de{' '}
              <span className="text-gray-800 font-semibold">{total}</span>
            </span>
            {trialsQ.isFetching && !isLoading && (
              <span className="text-gray-400">carregando...</span>
            )}
          </div>
          <div className="space-y-3">
            {items.map((t) => <TrialCard key={t.nct_id} trial={t} />)}
          </div>
          <Pagination
            page={page}
            pages={pages}
            onPrevious={() => setPage((p) => Math.max(1, p - 1))}
            onNext={() => setPage((p) => Math.min(pages, p + 1))}
          />
        </>
      )}

      {/* Footer attribution */}
      <p className="text-[10px] text-gray-400 text-center pt-2 flex items-center justify-center gap-2">
        <span>Dados de</span>
        <a
          href="https://clinicaltrials.gov"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-gray-500 hover:text-green-700 transition-colors"
        >
          ClinicalTrials.gov <ExternalLink size={9} />
        </a>
        {kpis.latest_trial_start && (
          <span>· trial mais recente iniciou em {fmtDate(kpis.latest_trial_start)}</span>
        )}
      </p>
    </div>
  )
}
