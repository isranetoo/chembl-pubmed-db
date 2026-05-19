import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Stethoscope, Search, SlidersHorizontal, Building2, Activity, Target,
  ExternalLink, BarChart3, ArrowUpRight, TrendingUp, X,
} from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
  PieChart, Pie,
} from 'recharts'
import {
  useTrials, useTrialsStats, useTrialsSponsors, useTrialsConditions, useEndpointAnalysis,
} from '../lib/hooks'
import { formatNumber } from '../lib/utils'
import Section from '../components/Section'
import Loader from '../components/Loader'
import StatCard from '../components/StatCard'
import Pill from '../components/Pill'
import Pagination from '../components/Pagination'
import EmptyState from '../components/EmptyState'

const PAGE_SIZE = 15

const TOOLTIP_STYLE = {
  backgroundColor: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: 12,
  fontSize: 12,
  fontFamily: 'Kanit',
  color: '#1f2937',
  boxShadow: '0 4px 14px rgba(33,81,83,0.08)',
}

const STATUS_COLORS = {
  RECRUITING:               '#0d9488',
  ACTIVE_NOT_RECRUITING:    '#0369a1',
  COMPLETED:                '#2f6b14',
  NOT_YET_RECRUITING:       '#7c3aed',
  TERMINATED:               '#be185d',
  SUSPENDED:                '#b45309',
  WITHDRAWN:                '#9ca3af',
  UNKNOWN:                  '#64748b',
  ENROLLING_BY_INVITATION:  '#0d9488',
  APPROVED_FOR_MARKETING:   '#16a34a',
}

const PHASE_COLORS = {
  EARLY_PHASE1: '#94a3b8',
  PHASE1:       '#64748b',
  PHASE2:       '#b45309',
  PHASE3:       '#0369a1',
  PHASE4:       '#2f6b14',
  NA:           '#e5e7eb',
}

function statusBadge(s) {
  const color = STATUS_COLORS[s] || '#64748b'
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border"
      style={{ borderColor: color + '55', backgroundColor: color + '15', color }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
      {s?.replace(/_/g, ' ')}
    </span>
  )
}

function phaseBadge(p) {
  const color = PHASE_COLORS[p] || '#9ca3af'
  return (
    <span
      key={p}
      className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold font-mono"
      style={{ backgroundColor: color + '20', color }}
    >
      {p}
    </span>
  )
}

// ── Filtros ─────────────────────────────────────────────────────
function FiltersBar({ filters, onChange, onClear, sponsors }) {
  return (
    <Section title="Filtros" delay={0.05}>
      <div className="flex items-center gap-2 mb-3 text-gray-500">
        <SlidersHorizontal size={14} />
        <span className="text-xs">Combine filtros — todos aplicam ao mesmo tempo</span>
        {Object.values(filters).some((v) => v && v !== 'desc' && v !== 'start_date') && (
          <button
            onClick={onClear}
            className="ml-auto inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
          >
            <X size={11} /> Limpar
          </button>
        )}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <div className="lg:col-span-2 xl:col-span-2">
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Busca</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className="glass-input w-full pl-9"
              placeholder="Título, sponsor ou condição..."
              value={filters.q}
              onChange={(e) => onChange({ q: e.target.value })}
            />
          </div>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Status</label>
          <select className="glass-input w-full" value={filters.status} onChange={(e) => onChange({ status: e.target.value })}>
            <option value="">Todos</option>
            <option value="RECRUITING">Recruiting</option>
            <option value="ACTIVE_NOT_RECRUITING">Active, not recruiting</option>
            <option value="COMPLETED">Completed</option>
            <option value="NOT_YET_RECRUITING">Not yet recruiting</option>
            <option value="TERMINATED">Terminated</option>
            <option value="SUSPENDED">Suspended</option>
            <option value="WITHDRAWN">Withdrawn</option>
            <option value="UNKNOWN">Unknown</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Fase</label>
          <select className="glass-input w-full" value={filters.phase} onChange={(e) => onChange({ phase: e.target.value })}>
            <option value="">Todas</option>
            <option value="EARLY_PHASE1">Early Phase 1</option>
            <option value="PHASE1">Phase 1</option>
            <option value="PHASE2">Phase 2</option>
            <option value="PHASE3">Phase 3</option>
            <option value="PHASE4">Phase 4</option>
            <option value="NA">N/A</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Sponsor</label>
          <input
            list="sponsors-suggest"
            className="glass-input w-full"
            placeholder="Pfizer, Novartis..."
            value={filters.sponsor}
            onChange={(e) => onChange({ sponsor: e.target.value })}
          />
          <datalist id="sponsors-suggest">
            {(sponsors || []).slice(0, 30).map((s) => <option key={s.sponsor} value={s.sponsor} />)}
          </datalist>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Indicação</label>
          <input
            className="glass-input w-full"
            placeholder="leukemia, melanoma..."
            value={filters.condition}
            onChange={(e) => onChange({ condition: e.target.value })}
          />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Study type</label>
          <select className="glass-input w-full" value={filters.study_type} onChange={(e) => onChange({ study_type: e.target.value })}>
            <option value="">Todos</option>
            <option value="INTERVENTIONAL">Interventional</option>
            <option value="OBSERVATIONAL">Observational</option>
            <option value="EXPANDED_ACCESS">Expanded Access</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Ordenar por</label>
          <div className="flex gap-2">
            <select className="glass-input flex-1" value={filters.sort_by} onChange={(e) => onChange({ sort_by: e.target.value })}>
              <option value="start_date">Início</option>
              <option value="enrollment">Recrutamento</option>
              <option value="nct_id">NCT id</option>
            </select>
            <select className="glass-input w-20" value={filters.sort_order} onChange={(e) => onChange({ sort_order: e.target.value })}>
              <option value="desc">↓</option>
              <option value="asc">↑</option>
            </select>
          </div>
        </div>
      </div>
    </Section>
  )
}

// ── Trial Card ──────────────────────────────────────────────────
function TrialCard({ t }) {
  return (
    <div className="rounded-xl bg-white border border-gray-200 p-4 hover:shadow-md hover:border-sky-300 transition-all">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            <a
              href={`https://clinicaltrials.gov/study/${t.nct_id}`}
              target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] font-mono font-semibold text-sky-800 bg-sky-50 border border-sky-200 px-2 py-0.5 rounded hover:bg-sky-100"
            >
              {t.nct_id} <ExternalLink size={9} />
            </a>
            {t.status && statusBadge(t.status)}
            {(t.phases || []).map((p) => phaseBadge(p))}
            {t.study_type && (
              <span className="text-[10px] text-gray-500 italic">{t.study_type.replace(/_/g, ' ')}</span>
            )}
          </div>
          <p className="text-sm font-medium text-gray-800 leading-snug line-clamp-2" title={t.title}>{t.title}</p>
        </div>
        {t.enrollment != null && (
          <div className="flex-shrink-0 text-right">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Enrollment</p>
            <p className="text-sm font-mono font-bold text-gray-800">{formatNumber(t.enrollment)}</p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-gray-600 mt-2">
        {t.sponsor && (
          <span className="inline-flex items-center gap-1">
            <Building2 size={11} className="text-gray-400" /> {t.sponsor}
          </span>
        )}
        {t.start_date && <span>Início: <span className="font-mono">{t.start_date}</span></span>}
        {t.primary_completion_date && <span>Conclusão prevista: <span className="font-mono">{t.primary_completion_date}</span></span>}
        {t.locations_count > 0 && <span>{t.locations_count} sites</span>}
      </div>

      {(t.conditions || []).length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {t.conditions.slice(0, 5).map((c) => (
            <span key={c} className="text-[10px] px-1.5 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200">
              {c}
            </span>
          ))}
          {t.conditions.length > 5 && (
            <span className="text-[10px] text-gray-400">+{t.conditions.length - 5}</span>
          )}
        </div>
      )}

      {t.primary_endpoint && (
        <div className="mt-2 text-[11px] text-gray-600">
          <span className="text-[9px] uppercase tracking-wider text-gray-400 font-semibold mr-1">Endpoint:</span>
          <span className="line-clamp-1" title={t.primary_endpoint}>{t.primary_endpoint}</span>
        </div>
      )}

      {(t.chembl_ids || []).length > 0 && (
        <div className="flex flex-wrap items-center gap-1 mt-3 pt-3 border-t border-gray-100">
          <span className="text-[9px] uppercase tracking-wider text-gray-400 font-semibold mr-1">Compostos:</span>
          {t.chembl_ids.slice(0, 4).map((cid, i) => (
            <Link
              key={cid}
              to={`/compounds/${cid}`}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-mono bg-green-50 text-green-800 border border-green-200 hover:bg-green-100"
            >
              {t.compounds?.[i] || cid} <ArrowUpRight size={9} />
            </Link>
          ))}
          {t.chembl_ids.length > 4 && (
            <span className="text-[10px] text-gray-400">+{t.chembl_ids.length - 4}</span>
          )}
        </div>
      )}
    </div>
  )
}

// ── Página principal ─────────────────────────────────────────────
export default function TrialsPage() {
  const [filters, setFilters] = useState({
    q: '', status: '', phase: '', sponsor: '', condition: '',
    study_type: '', sort_by: 'start_date', sort_order: 'desc',
  })
  const [page, setPage] = useState(1)

  const queryParams = useMemo(() => ({
    page, size: PAGE_SIZE,
    q: filters.q || undefined,
    status: filters.status || undefined,
    phase: filters.phase || undefined,
    sponsor: filters.sponsor || undefined,
    condition: filters.condition || undefined,
    study_type: filters.study_type || undefined,
    sort_by: filters.sort_by,
    sort_order: filters.sort_order,
  }), [filters, page])

  const onFilter = (patch) => {
    setFilters((p) => ({ ...p, ...patch }))
    setPage(1)
  }
  const clearFilters = () => {
    setFilters({ q: '', status: '', phase: '', sponsor: '', condition: '', study_type: '', sort_by: 'start_date', sort_order: 'desc' })
    setPage(1)
  }

  const statsQ      = useTrialsStats()
  const trialsQ     = useTrials(queryParams)
  const sponsorsQ   = useTrialsSponsors({ size: 15 })
  const conditionsQ = useTrialsConditions({ size: 20 })
  const endpointsQ  = useEndpointAnalysis({
    condition: filters.condition || undefined,
    sponsor: filters.sponsor || undefined,
    phase: filters.phase || undefined,
  })

  const stats = statsQ.data || {}

  const phaseChartData = useMemo(() => {
    const order = ['EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'NA']
    return order
      .filter((p) => stats.by_phase?.[p])
      .map((p) => ({ phase: p.replace('PHASE', 'P').replace('EARLY_P', 'EP'), count: stats.by_phase[p], color: PHASE_COLORS[p] }))
  }, [stats])

  const statusChartData = useMemo(() => {
    const entries = Object.entries(stats.by_status || {})
    return entries
      .map(([k, v]) => ({ status: k.replace(/_/g, ' '), key: k, count: v, color: STATUS_COLORS[k] || '#64748b' }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)
  }, [stats])

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-sky-700 mb-2">Clinical Trials</p>
        <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-gray-800">
          Ensaios <span className="bg-gradient-to-br from-green-600 to-green-900 text-transparent bg-clip-text">Clínicos</span>
        </h1>
        <p className="mt-2 text-sm text-neutral-600 max-w-2xl">
          Catálogo cross-composto de trials sincronizados da ClinicalTrials.gov. Filtre por fase, sponsor, indicação e analise endpoints primários comuns.
        </p>
      </div>

      {/* KPIs */}
      {statsQ.isLoading ? <Loader label="Carregando estatísticas..." /> : (
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
          <StatCard label="Trials cacheados" value={stats.total_trials} icon={Stethoscope} color="sky" delay={0.05}
            helper={`${formatNumber(stats.distinct_compounds_with_trials)} compostos cobertos`} />
          <StatCard label="Recrutando" value={stats.recruiting_trials} icon={Activity} color="teal" delay={0.1}
            helper="status RECRUITING" />
          <StatCard label="Phase 3+" value={(stats.phase3_trials || 0) + (stats.phase4_trials || 0)} icon={Target} color="emerald" delay={0.15}
            helper={`${formatNumber(stats.phase3_trials)} P3 · ${formatNumber(stats.phase4_trials)} P4`} />
          <StatCard label="Sponsors distintos" value={stats.unique_sponsors} icon={Building2} color="violet" delay={0.2}
            helper={`${formatNumber(stats.unique_conditions)} indicações`} />
        </div>
      )}

      {/* Charts row */}
      {!statsQ.isLoading && (statusChartData.length > 0 || phaseChartData.length > 0) && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Section title="Distribuição por status" delay={0.25}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={statusChartData} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" allowDecimals={false} />
                <YAxis dataKey="status" type="category" tick={{ fill: '#4b5563', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" width={150} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}
                  onClick={(d) => onFilter({ status: d?.payload?.key })}
                  style={{ cursor: 'pointer' }}>
                  {statusChartData.map((d, i) => <Cell key={i} fill={d.color} fillOpacity={0.85} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="text-[10px] text-gray-400 text-center mt-1">Clique numa barra pra filtrar a lista</p>
          </Section>

          <Section title="Distribuição por fase" delay={0.3}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={phaseChartData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                <XAxis dataKey="phase" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" allowDecimals={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {phaseChartData.map((d, i) => <Cell key={i} fill={d.color} fillOpacity={0.85} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Section>
        </div>
      )}

      {/* Filtros */}
      <FiltersBar
        filters={filters}
        onChange={onFilter}
        onClear={clearFilters}
        sponsors={sponsorsQ.data?.items}
      />

      {/* Lista de trials */}
      <Section title={trialsQ.data ? `${formatNumber(trialsQ.data.total)} trials encontrados` : 'Trials'} delay={0.35}>
        {trialsQ.isLoading ? <Loader label="Buscando trials..." /> :
         trialsQ.error ? <div className="text-rose-700 text-sm">{trialsQ.error.message}</div> :
         !trialsQ.data?.items?.length ? <EmptyState description="Sem trials para esses filtros. Tente relaxar os critérios." /> : (
          <>
            <div className="space-y-3">
              {trialsQ.data.items.map((t) => <TrialCard key={t.nct_id} t={t} />)}
            </div>
            <div className="mt-4">
              <Pagination
                page={trialsQ.data.page}
                pages={trialsQ.data.pages}
                onPrevious={() => setPage((p) => Math.max(1, p - 1))}
                onNext={() => setPage((p) => Math.min(trialsQ.data.pages, p + 1))}
              />
            </div>
          </>
        )}
      </Section>

      {/* Top sponsors + Top conditions */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Top sponsors" delay={0.4}>
          <p className="text-xs text-neutral-500 mb-3">Clique pra filtrar a lista de trials acima.</p>
          {sponsorsQ.isLoading ? <Loader /> :
           !sponsorsQ.data?.items?.length ? <p className="text-sm text-neutral-500 text-center py-4">Sem dados.</p> : (
            <div className="space-y-1.5 max-h-96 overflow-y-auto">
              {sponsorsQ.data.items.map((s) => {
                const isActive = filters.sponsor === s.sponsor
                return (
                  <button
                    key={s.sponsor}
                    onClick={() => onFilter({ sponsor: isActive ? '' : s.sponsor })}
                    className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-left transition-colors border ${
                      isActive ? 'bg-violet-50 border-violet-300' : 'bg-white border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <span className="text-xs text-gray-800 font-medium truncate" title={s.sponsor}>{s.sponsor}</span>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {s.recruiting_trials > 0 && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
                          {s.recruiting_trials} rec
                        </span>
                      )}
                      {s.phase3_trials > 0 && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200">
                          {s.phase3_trials} P3
                        </span>
                      )}
                      <span className="text-xs font-mono font-bold text-gray-700 w-12 text-right">
                        {formatNumber(s.trial_count)}
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </Section>

        <Section title="Top indicações" delay={0.45}>
          <p className="text-xs text-neutral-500 mb-3">Clique pra filtrar a lista de trials acima.</p>
          {conditionsQ.isLoading ? <Loader /> :
           !conditionsQ.data?.items?.length ? <p className="text-sm text-neutral-500 text-center py-4">Sem dados.</p> : (
            <div className="flex flex-wrap gap-1.5 max-h-96 overflow-y-auto">
              {conditionsQ.data.items.map((c) => {
                const isActive = filters.condition === c.condition
                return (
                  <button
                    key={c.condition}
                    onClick={() => onFilter({ condition: isActive ? '' : c.condition })}
                    className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] border transition-colors ${
                      isActive
                        ? 'bg-rose-100 text-rose-800 border-rose-300'
                        : 'bg-white text-gray-700 border-gray-200 hover:bg-rose-50 hover:border-rose-200'
                    }`}
                  >
                    <span>{c.condition}</span>
                    <span className="text-[9px] text-gray-500 font-mono">{c.trial_count}</span>
                  </button>
                )
              })}
            </div>
          )}
        </Section>
      </div>

      {/* Análise de endpoints */}
      <Section title="Análise de endpoints primários" delay={0.5}>
        <p className="text-xs text-neutral-500 mb-3 flex items-center gap-2">
          <TrendingUp size={12} className="text-green-700" />
          Classificação automática dos <code className="font-mono px-1">primary_endpoint</code> em buckets clínicos clássicos
          (PFS, OS, ORR, MTD, segurança, QoL…). Filtros acima (sponsor, indicação, fase) afetam esta análise.
        </p>

        {endpointsQ.isLoading ? <Loader label="Analisando endpoints..." /> :
         !endpointsQ.data?.buckets?.length ? <EmptyState description="Sem endpoints classificados pra esses filtros." /> : (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <p className="text-[11px] text-gray-500 mb-2">
                <strong>{formatNumber(endpointsQ.data.total_with_endpoint)}</strong> trials com endpoint preenchido ·
                {' '}<strong>{endpointsQ.data.buckets.length}</strong> categorias detectadas
              </p>
              <ResponsiveContainer width="100%" height={Math.max(280, endpointsQ.data.buckets.length * 28)}>
                <BarChart data={endpointsQ.data.buckets} layout="vertical" margin={{ top: 5, right: 30, bottom: 5, left: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                  <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" allowDecimals={false} />
                  <YAxis dataKey="label" type="category" tick={{ fill: '#4b5563', fontSize: 10 }}
                    stroke="rgba(31,41,55,0.1)" width={220} />
                  <Tooltip contentStyle={TOOLTIP_STYLE}
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const p = payload[0].payload
                      return (
                        <div className="bg-white border border-gray-200 rounded-xl shadow-md p-3 text-xs">
                          <p className="font-semibold text-gray-800 mb-1">{p.label}</p>
                          <p className="text-gray-700">{p.matches} trials</p>
                          {p.examples?.length > 0 && (
                            <>
                              <p className="text-[10px] text-gray-400 mt-2 uppercase tracking-wider">Exemplos:</p>
                              {p.examples.map((nct) => (
                                <p key={nct} className="font-mono text-[11px] text-sky-700">{nct}</p>
                              ))}
                            </>
                          )}
                        </div>
                      )
                    }} />
                  <Bar dataKey="matches" fill="#0369a1" fillOpacity={0.85} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div>
              <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-2">
                Palavras-chave de endpoints não-classificados
              </p>
              {!endpointsQ.data.top_phrases?.length ? (
                <p className="text-xs text-neutral-500">Sem padrões adicionais.</p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {endpointsQ.data.top_phrases.map((p) => (
                    <span key={p.phrase}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] bg-gray-50 border border-gray-200 text-gray-700">
                      <span className="font-mono">{p.phrase}</span>
                      <span className="text-[9px] text-gray-400">{p.count}</span>
                    </span>
                  ))}
                </div>
              )}
              <p className="text-[10px] text-gray-400 mt-3 leading-relaxed">
                Tokens frequentes nos endpoints fora dos buckets canônicos. Útil pra surfacing
                endpoints específicos da indicação (ex: <em>HbA1c</em> em diabetes, <em>viral load</em> em virologia).
              </p>
            </div>
          </div>
        )}
      </Section>
    </div>
  )
}
