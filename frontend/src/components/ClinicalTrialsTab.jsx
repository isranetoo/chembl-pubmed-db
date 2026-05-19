import { useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertCircle, Building2, CheckCircle2, ChevronRight,
  ExternalLink, FlaskConical, RefreshCw, TestTube, Users,
} from 'lucide-react'
import { useCompoundTrials, useSyncCompoundTrials } from '../lib/hooks'
import EmptyState from './EmptyState'
import Pagination from './Pagination'

const PAGE_SIZE = 10

// Mapa de cores por status — usado no badge dos cards.
const STATUS_STYLES = {
  RECRUITING:              'bg-emerald-500/15 text-emerald-300 border-emerald-500/25',
  ACTIVE_NOT_RECRUITING:   'bg-sky-500/15 text-sky-300 border-sky-500/25',
  ENROLLING_BY_INVITATION: 'bg-sky-500/15 text-sky-300 border-sky-500/25',
  COMPLETED:               'bg-slate-500/15 text-slate-300 border-slate-500/25',
  TERMINATED:              'bg-rose-500/15 text-rose-300 border-rose-500/25',
  WITHDRAWN:               'bg-rose-500/15 text-rose-300 border-rose-500/25',
  SUSPENDED:               'bg-amber-500/15 text-amber-300 border-amber-500/25',
  NOT_YET_RECRUITING:      'bg-violet-500/15 text-violet-300 border-violet-500/25',
}

const PHASE_OPTIONS = ['PHASE1', 'PHASE2', 'PHASE3', 'PHASE4']
const STATUS_OPTIONS = ['RECRUITING', 'ACTIVE_NOT_RECRUITING', 'COMPLETED', 'TERMINATED']

function statusClass(s) {
  return STATUS_STYLES[s] || 'bg-white/[0.06] text-white/60 border-white/10'
}

function fmtDate(s) {
  if (!s) return '—'
  return s.slice(0, 10)
}

// ── KPI strip ────────────────────────────────────────────────────────

function KpiCard({ label, value, gradient, icon: Icon }) {
  return (
    <div className={`relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br ${gradient} p-4 backdrop-blur-md transition-all hover:-translate-y-0.5 hover:border-white/20`}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] uppercase tracking-wider text-white/50">{label}</p>
        <Icon size={14} className="text-white/40" />
      </div>
      <p className="text-2xl font-bold text-white/90" style={{ fontFamily: 'Outfit' }}>{value ?? 0}</p>
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
      className="group block rounded-xl border border-white/[0.06] bg-white/[0.03] p-4 transition-all hover:-translate-y-0.5 hover:border-white/15 hover:bg-white/[0.05]"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <code className="text-[10px] font-mono text-emerald-300/60">{trial.nct_id}</code>
          <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium border ${statusClass(trial.status)}`}>
            {trial.status || '—'}
          </span>
          {(trial.phases || []).map((p) => (
            <span key={p} className="rounded-md px-1.5 py-0.5 text-[10px] font-medium bg-white/[0.04] text-white/50 border border-white/10">
              {p.replace('PHASE', 'Fase ')}
            </span>
          ))}
        </div>
        <ChevronRight size={14} className="text-white/30 group-hover:text-white/60 transition-colors flex-shrink-0 mt-0.5" />
      </div>

      <h3 className="text-sm text-white/85 leading-snug line-clamp-2 mb-2">{trial.title || 'Sem título'}</h3>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-x-3 gap-y-1.5 text-[11px] text-white/40">
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
        <p className="mt-2.5 text-[11px] text-white/35 leading-relaxed line-clamp-2">
          <span className="text-white/50 font-medium">Endpoint:</span> {trial.primary_endpoint}
        </p>
      )}
    </a>
  )
}

// ── Subcomponents ────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 animate-pulse">
      <div className="flex items-center gap-2 mb-3">
        <div className="h-3 w-20 rounded bg-white/[0.06]" />
        <div className="h-4 w-16 rounded bg-white/[0.06]" />
      </div>
      <div className="h-3 w-full rounded bg-white/[0.06] mb-2" />
      <div className="h-3 w-3/4 rounded bg-white/[0.06] mb-3" />
      <div className="grid grid-cols-4 gap-2">
        <div className="h-2.5 rounded bg-white/[0.04]" />
        <div className="h-2.5 rounded bg-white/[0.04]" />
        <div className="h-2.5 rounded bg-white/[0.04]" />
        <div className="h-2.5 rounded bg-white/[0.04]" />
      </div>
    </div>
  )
}

function ErrorCard({ message, onRetry }) {
  return (
    <div className="rounded-2xl border border-rose-500/20 bg-rose-500/[0.06] p-6 text-center">
      <AlertCircle size={20} className="text-rose-400 mx-auto mb-2" />
      <p className="text-sm text-rose-200/80 mb-3">{message}</p>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-200 hover:bg-rose-500/20 transition-colors"
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
        <KpiCard label="Total"      value={kpis.total_trials}      gradient="from-cyan-500/[0.08] to-cyan-500/[0.02]"     icon={FlaskConical} />
        <KpiCard label="Recrutando" value={kpis.recruiting_trials} gradient="from-emerald-500/[0.08] to-emerald-500/[0.02]" icon={Activity} />
        <KpiCard label="Fase 3"     value={kpis.phase3_trials}     gradient="from-violet-500/[0.08] to-violet-500/[0.02]"   icon={TestTube} />
        <KpiCard label="Fase 4"     value={kpis.phase4_trials}     gradient="from-amber-500/[0.08] to-amber-500/[0.02]"     icon={CheckCircle2} />
      </div>

      {/* Action bar */}
      <div className="flex flex-wrap items-center gap-2 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
        <span className="text-[10px] uppercase tracking-wider text-white/30 mr-1">Fase:</span>
        {PHASE_OPTIONS.map((p) => (
          <button
            key={p}
            onClick={() => setPhaseFilter(phaseFilter === p ? null : p)}
            className={`rounded-md border px-2 py-1 text-[11px] transition-colors ${
              phaseFilter === p
                ? 'bg-violet-500/15 text-violet-200 border-violet-500/30'
                : 'bg-white/[0.03] text-white/45 border-white/[0.08] hover:text-white/70'
            }`}
          >
            {p.replace('PHASE', 'Fase ')}
          </button>
        ))}
        <span className="text-[10px] uppercase tracking-wider text-white/30 ml-3 mr-1">Status:</span>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(statusFilter === s ? null : s)}
            className={`rounded-md border px-2 py-1 text-[11px] transition-colors ${
              statusFilter === s
                ? 'bg-emerald-500/15 text-emerald-200 border-emerald-500/30'
                : 'bg-white/[0.03] text-white/45 border-white/[0.08] hover:text-white/70'
            }`}
          >
            {s.replace(/_/g, ' ')}
          </button>
        ))}

        <div className="ml-auto flex items-center gap-2">
          {syncMut.error && (
            <span className="text-[11px] text-rose-300/80">{syncMut.error.message}</span>
          )}
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-200 hover:bg-emerald-500/15 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
        <div className="rounded-2xl glass p-12 text-center animate-fade-in">
          <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mx-auto mb-4">
            <FlaskConical size={24} className="text-white/20" />
          </div>
          <h3 className="text-base font-semibold text-white/70 mb-1" style={{ fontFamily: 'Outfit' }}>
            Nenhum ensaio cacheado ainda
          </h3>
          <p className="text-sm text-white/30 mb-5">
            Busque na ClinicalTrials.gov pelo nome do composto.
          </p>
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-200 hover:bg-emerald-500/15 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={13} className={isSyncing ? 'animate-spin' : ''} />
            {isSyncing ? 'Buscando...' : 'Buscar trials agora'}
          </button>
        </div>
      ) : items.length === 0 ? (
        <EmptyState description="Nenhum trial bate com os filtros." />
      ) : (
        <>
          <div className="flex items-center justify-between px-1 text-[11px] text-white/40">
            <span>
              Mostrando {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} de{' '}
              <span className="text-white/70 font-medium">{total}</span>
            </span>
            {trialsQ.isFetching && !isLoading && (
              <span className="text-white/30">carregando...</span>
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
      <p className="text-[10px] text-white/25 text-center pt-2 flex items-center justify-center gap-2">
        <span>Dados de</span>
        <a
          href="https://clinicaltrials.gov"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-white/40 hover:text-white/60 transition-colors"
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
