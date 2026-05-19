import { useMemo, useState } from 'react'
import {
  BarChart3, SlidersHorizontal, Activity, Crosshair,
  Atom, ShieldCheck, Award, AlertTriangle,
} from 'lucide-react'
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ReferenceLine, BarChart, Bar, Cell, PieChart, Pie, LineChart, Line,
} from 'recharts'
import { useCompounds, useTargets, useArticles } from '../lib/hooks'
import { formatNumber, phaseLabel, getPhaseColor } from '../lib/utils'
import Section from '../components/Section'
import Loader from '../components/Loader'
import StatCard from '../components/StatCard'

// ── Cores consistentes com o resto do app ────────────────────
const COLORS = {
  primary: '#2f6b14',
  primaryLight: '#5c8d2f',
  sky: '#0369a1',
  amber: '#b45309',
  rose: '#be185d',
  violet: '#7c3aed',
  teal: '#0d9488',
  slate: '#64748b',
}

const TOOLTIP_STYLE = {
  backgroundColor: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: 12,
  fontSize: 12,
  fontFamily: 'Kanit',
  color: '#1f2937',
  boxShadow: '0 4px 14px rgba(33,81,83,0.08)',
}

// ─────────────────────────────────────────────────────────────
// Helpers — agregações sobre a amostra de compostos
// ─────────────────────────────────────────────────────────────

function buildHistogram(values, bins, range) {
  const [min, max] = range
  const step = (max - min) / bins
  const counts = Array.from({ length: bins }, (_, i) => ({
    bin: `${(min + i * step).toFixed(1)}`,
    range: [min + i * step, min + (i + 1) * step],
    count: 0,
  }))
  values.forEach((v) => {
    if (v == null || Number.isNaN(v)) return
    let idx = Math.floor((v - min) / step)
    if (idx < 0) idx = 0
    if (idx >= bins) idx = bins - 1
    counts[idx].count += 1
  })
  return counts
}

function phaseFromCount(items) {
  const buckets = { 4: 0, 3: 0, 2: 0, 1: 0, 0: 0 }
  items.forEach((c) => {
    const p = Number(c.max_clinical_phase)
    if (p >= 4) buckets[4] += 1
    else if (p >= 3) buckets[3] += 1
    else if (p >= 2) buckets[2] += 1
    else if (p >= 1) buckets[1] += 1
    else buckets[0] += 1
  })
  return [
    { phase: 'Preclinical', count: buckets[0], color: COLORS.slate },
    { phase: 'Phase 1', count: buckets[1], color: '#94a3b8' },
    { phase: 'Phase 2', count: buckets[2], color: COLORS.amber },
    { phase: 'Phase 3', count: buckets[3], color: COLORS.sky },
    { phase: 'Approved', count: buckets[4], color: COLORS.primary },
  ]
}

// ─────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [filters, setFilters] = useState({
    min_qed: '',
    min_phase: '',
    lipinski: '',
    min_mw: '',
    max_mw: '',
  })

  const queryParams = useMemo(() => ({
    size: 100,
    min_qed: filters.min_qed || undefined,
    min_phase: filters.min_phase || undefined,
    lipinski: filters.lipinski === '' ? undefined : filters.lipinski,
    min_mw: filters.min_mw || undefined,
    max_mw: filters.max_mw || undefined,
  }), [filters])

  const { data: compoundsData, isLoading: loadingCompounds, error: compoundsError } = useCompounds(queryParams)
  const { data: targetsData, isLoading: loadingTargets } = useTargets({ size: 15 })
  const { data: articlesData, isLoading: loadingArticles } = useArticles({ size: 100, min_year: 2000 })

  const compounds = compoundsData?.items ?? []
  const sampleSize = compounds.length
  const totalMatching = compoundsData?.total ?? 0

  // KPIs
  const kpis = useMemo(() => {
    if (sampleSize === 0) return { avgQed: null, avgMw: null, pctLipinski: null, pctPhase4: null }
    const qeds = compounds.map((c) => c.qed).filter((v) => v != null)
    const mws = compounds.map((c) => c.mol_weight).filter((v) => v != null)
    const lipOk = compounds.filter((c) => c.ro5_violations === 0).length
    const approved = compounds.filter((c) => Number(c.max_clinical_phase) >= 4).length
    return {
      avgQed: qeds.length ? qeds.reduce((a, b) => a + Number(b), 0) / qeds.length : null,
      avgMw: mws.length ? mws.reduce((a, b) => a + Number(b), 0) / mws.length : null,
      pctLipinski: (lipOk / sampleSize) * 100,
      pctPhase4: (approved / sampleSize) * 100,
    }
  }, [compounds, sampleSize])

  // Chemical space scatter (ALogP × PSA), pinta por fase
  const scatterData = useMemo(() => (
    compounds
      .filter((c) => c.alogp != null && c.psa != null)
      .map((c) => ({
        x: Number(c.alogp),
        y: Number(c.psa),
        z: Number(c.mol_weight) || 0,
        name: c.name || c.chembl_id,
        chembl_id: c.chembl_id,
        phase: Number(c.max_clinical_phase) || 0,
        qed: c.qed,
      }))
  ), [compounds])

  // Histogramas
  const qedHistogram = useMemo(
    () => buildHistogram(compounds.map((c) => c.qed != null ? Number(c.qed) : null), 10, [0, 1]),
    [compounds],
  )
  const mwHistogram = useMemo(
    () => buildHistogram(compounds.map((c) => c.mol_weight != null ? Number(c.mol_weight) : null), 10, [0, 800]),
    [compounds],
  )

  // Pipeline clínico
  const pipelineData = useMemo(() => phaseFromCount(compounds), [compounds])

  // Distribuição de violações Ro5
  const ro5Data = useMemo(() => {
    const buckets = [0, 1, 2, 3, 4].map((n) => ({ name: `${n} viol.`, value: 0, raw: n }))
    compounds.forEach((c) => {
      const v = Math.min(Math.max(Number(c.ro5_violations) || 0, 0), 4)
      buckets[v].value += 1
    })
    return buckets.filter((b) => b.value > 0)
  }, [compounds])
  const RO5_COLORS = [COLORS.primary, COLORS.amber, COLORS.rose, '#9f1239', '#7f1d1d']

  // Top targets (por nº de compostos testados)
  const topTargets = useMemo(() => (
    (targetsData?.items ?? [])
      .filter((t) => t.compounds_tested > 0)
      .slice(0, 10)
      .map((t) => ({
        name: t.name?.length > 30 ? t.name.slice(0, 28) + '…' : t.name,
        full_name: t.name,
        compounds_tested: Number(t.compounds_tested) || 0,
        organism: t.organism,
      }))
  ), [targetsData])

  // Artigos por ano
  const articlesByYear = useMemo(() => {
    const map = new Map()
    ;(articlesData?.items ?? []).forEach((a) => {
      if (!a.pub_year) return
      map.set(a.pub_year, (map.get(a.pub_year) || 0) + 1)
    })
    return Array.from(map.entries())
      .map(([year, count]) => ({ year, count }))
      .sort((a, b) => a.year - b.year)
  }, [articlesData])

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-green-700 mb-2">Analytics</p>
        <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-gray-800">
          Análise <span className="bg-gradient-to-br from-green-600 to-green-900 text-transparent bg-clip-text">Química</span>
        </h1>
        <p className="mt-2 text-sm text-neutral-600">
          Distribuições, espaço químico e pipeline clínico sobre a amostra do banco. Para calculadoras químicas, abra a página <span className="font-medium text-gray-700">Ferramentas</span>.
        </p>
      </div>

      {/* Filtros globais */}
      <Section title="Filtros" delay={0.05}>
        <div className="flex items-center gap-2 mb-4 text-gray-500">
          <SlidersHorizontal size={14} />
          <span className="text-xs">Aplica-se a todos os gráficos abaixo (amostra: até 100 compostos)</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">QED mínimo</label>
            <input className="glass-input w-full" type="number" step="0.1" min="0" max="1"
              placeholder="0.0 – 1.0"
              value={filters.min_qed}
              onChange={(e) => setFilters((p) => ({ ...p, min_qed: e.target.value }))} />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Fase clínica</label>
            <select className="glass-input w-full" value={filters.min_phase}
              onChange={(e) => setFilters((p) => ({ ...p, min_phase: e.target.value }))}>
              <option value="">Todas</option>
              <option value="1">Phase 1+</option>
              <option value="2">Phase 2+</option>
              <option value="3">Phase 3+</option>
              <option value="4">Approved</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Lipinski</label>
            <select className="glass-input w-full" value={filters.lipinski}
              onChange={(e) => setFilters((p) => ({ ...p, lipinski: e.target.value }))}>
              <option value="">Todos</option>
              <option value="true">Passa</option>
              <option value="false">Falha</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">MW mínimo</label>
            <input className="glass-input w-full" type="number" step="10" min="0"
              placeholder="ex: 150"
              value={filters.min_mw}
              onChange={(e) => setFilters((p) => ({ ...p, min_mw: e.target.value }))} />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">MW máximo</label>
            <input className="glass-input w-full" type="number" step="10" min="0"
              placeholder="ex: 500"
              value={filters.max_mw}
              onChange={(e) => setFilters((p) => ({ ...p, max_mw: e.target.value }))} />
          </div>
        </div>
        <div className="mt-3 flex items-center gap-3 text-xs text-neutral-500">
          <span className="inline-flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-600" />
            {formatNumber(totalMatching)} compostos no filtro · amostra de {formatNumber(sampleSize)}
          </span>
        </div>
      </Section>

      {compoundsError && (
        <div className="bg-white border border-rose-300 rounded-xl p-5 text-rose-700 text-sm">{compoundsError.message}</div>
      )}

      {loadingCompounds ? (
        <Loader label="Computando estatísticas..." />
      ) : sampleSize === 0 ? (
        <div className="bg-white border border-gray-200 rounded-2xl shadow-card p-12 text-center">
          <BarChart3 size={32} className="mx-auto text-gray-400 mb-3" />
          <p className="text-sm text-neutral-500">Nenhum composto bate com os filtros. Relaxe os critérios.</p>
        </div>
      ) : (
        <>
          {/* KPIs */}
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="QED médio"
              value={kpis.avgQed != null ? kpis.avgQed.toFixed(3) : '—'}
              icon={Award}
              color="emerald"
              delay={0.05}
              helper="Drug-likeness 0–1"
            />
            <StatCard
              label="MW médio (Da)"
              value={kpis.avgMw != null ? kpis.avgMw.toFixed(1) : '—'}
              icon={Atom}
              color="sky"
              delay={0.1}
              helper="Peso molecular"
            />
            <StatCard
              label="Lipinski OK"
              value={kpis.pctLipinski != null ? kpis.pctLipinski.toFixed(0) + '%' : '—'}
              icon={ShieldCheck}
              color="violet"
              delay={0.15}
              helper="ro5_violations = 0"
            />
            <StatCard
              label="Aprovados (FDA)"
              value={kpis.pctPhase4 != null ? kpis.pctPhase4.toFixed(0) + '%' : '—'}
              icon={Activity}
              color="amber"
              delay={0.2}
              helper="max_phase = 4 da amostra"
            />
          </div>

          {/* Chemical space */}
          <Section title="Espaço químico — ALogP × PSA" delay={0.25}>
            <p className="text-xs text-neutral-500 mb-3">
              Cada ponto é um composto da amostra. Linhas tracejadas marcam Lipinski (ALogP=5) e Veber (PSA=140 Å²).
              Cores indicam fase clínica máxima.
            </p>
            <ResponsiveContainer width="100%" height={380}>
              <ScatterChart margin={{ top: 10, right: 30, bottom: 30, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                <XAxis
                  type="number" dataKey="x" name="ALogP" domain={[-2, 10]}
                  label={{ value: 'ALogP', position: 'bottom', offset: 0, style: { fill: '#6b7280', fontSize: 11 } }}
                  tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)"
                />
                <YAxis
                  type="number" dataKey="y" name="PSA" domain={[0, 250]}
                  label={{ value: 'PSA (Å²)', angle: -90, position: 'insideLeft', style: { fill: '#6b7280', fontSize: 11 } }}
                  tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)"
                />
                <ReferenceLine x={5} stroke="#d97706" strokeDasharray="6 4"
                  label={{ value: 'Lipinski (ALogP=5)', position: 'top', style: { fill: '#b45309', fontSize: 9 } }} />
                <ReferenceLine y={140} stroke="#be185d" strokeDasharray="6 4"
                  label={{ value: 'Veber (PSA=140)', position: 'right', style: { fill: '#9d174d', fontSize: 9 } }} />
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    const p = payload[0].payload
                    return (
                      <div className="bg-white border border-gray-200 rounded-xl shadow-md p-3 text-xs">
                        <p className="font-semibold text-gray-800 mb-1">{p.name}</p>
                        <p className="font-mono text-gray-500 text-[10px] mb-2">{p.chembl_id}</p>
                        <p className="text-gray-700">ALogP: <span className="font-mono">{p.x?.toFixed(2)}</span></p>
                        <p className="text-gray-700">PSA: <span className="font-mono">{p.y?.toFixed(1)} Å²</span></p>
                        <p className="text-gray-700">MW: <span className="font-mono">{p.z?.toFixed(1)} Da</span></p>
                        <p className="text-gray-700">QED: <span className="font-mono">{p.qed != null ? Number(p.qed).toFixed(3) : '—'}</span></p>
                        <p className="text-gray-700">Fase: <span className="font-mono">{phaseLabel(p.phase)}</span></p>
                      </div>
                    )
                  }}
                />
                <Scatter data={scatterData}>
                  {scatterData.map((d, i) => (
                    <Cell key={i} fill={getPhaseColor(d.phase)} fillOpacity={0.7} stroke={getPhaseColor(d.phase)} strokeWidth={1} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-3 mt-3 text-[11px] text-gray-600">
              {[
                { p: 4, l: 'Approved' },
                { p: 3, l: 'Phase 3' },
                { p: 2, l: 'Phase 2' },
                { p: 0, l: 'Preclinical/early' },
              ].map((x) => (
                <span key={x.p} className="inline-flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: getPhaseColor(x.p) }} />
                  {x.l}
                </span>
              ))}
            </div>
          </Section>

          {/* Distribuições */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Section title="Distribuição de QED" delay={0.3}>
              <p className="text-xs text-neutral-500 mb-2">Drug-likeness 0–1, mais alto = mais drug-like</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={qedHistogram} margin={{ top: 10, right: 10, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                  <XAxis dataKey="bin" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" allowDecimals={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" name="Compostos" fill={COLORS.primary} fillOpacity={0.8} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Section>

            <Section title="Distribuição de MW (Da)" delay={0.35}>
              <p className="text-xs text-neutral-500 mb-2">Peso molecular — Lipinski sugere ≤ 500 Da</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={mwHistogram} margin={{ top: 10, right: 10, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                  <XAxis dataKey="bin" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" allowDecimals={false} />
                  <ReferenceLine x="500.0" stroke="#d97706" strokeDasharray="4 4"
                    label={{ value: '500 Da', position: 'top', style: { fill: '#b45309', fontSize: 9 } }} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" name="Compostos" fill={COLORS.sky} fillOpacity={0.8} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Section>
          </div>

          {/* Pipeline + Ro5 */}
          <div className="grid gap-4 lg:grid-cols-3">
            <Section title="Pipeline clínico" delay={0.4} className="lg:col-span-2">
              <p className="text-xs text-neutral-500 mb-2">Compostos da amostra por fase clínica máxima</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={pipelineData} layout="vertical" margin={{ top: 5, right: 30, bottom: 5, left: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                  <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" allowDecimals={false} />
                  <YAxis dataKey="phase" type="category" tick={{ fill: '#4b5563', fontSize: 11 }} stroke="rgba(31,41,55,0.1)" width={90} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {pipelineData.map((d, i) => (
                      <Cell key={i} fill={d.color} fillOpacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Section>

            <Section title="Violações Ro5" delay={0.45}>
              <p className="text-xs text-neutral-500 mb-2">Quantas regras de Lipinski cada composto viola</p>
              {ro5Data.length === 0 ? (
                <p className="text-sm text-neutral-500 text-center py-8">Sem dados.</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={ro5Data} dataKey="value" nameKey="name"
                      cx="50%" cy="50%" innerRadius={45} outerRadius={85} paddingAngle={2}
                    >
                      {ro5Data.map((entry, i) => (
                        <Cell key={i} fill={RO5_COLORS[entry.raw] || COLORS.slate} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'Kanit', color: '#4b5563' }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Section>
          </div>

          {/* Top Targets + Articles */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Section title="Top alvos por compostos testados" delay={0.5}>
              <p className="text-xs text-neutral-500 mb-2">Top 10 do banco (independente dos filtros acima)</p>
              {loadingTargets ? (
                <Loader label="Carregando targets..." />
              ) : topTargets.length === 0 ? (
                <p className="text-sm text-neutral-500 text-center py-8">Sem dados.</p>
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={topTargets} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                    <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" allowDecimals={false} />
                    <YAxis dataKey="name" type="category" tick={{ fill: '#4b5563', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" width={140} />
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        const p = payload[0].payload
                        return (
                          <div className="bg-white border border-gray-200 rounded-xl shadow-md p-3 text-xs max-w-xs">
                            <p className="font-semibold text-gray-800 mb-1">{p.full_name}</p>
                            {p.organism && <p className="text-gray-500 text-[10px] italic mb-1">{p.organism}</p>}
                            <p className="text-gray-700">Compostos testados: <span className="font-mono">{p.compounds_tested}</span></p>
                          </div>
                        )
                      }}
                    />
                    <Bar dataKey="compounds_tested" fill={COLORS.violet} fillOpacity={0.85} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Section>

            <Section title="Publicações por ano" delay={0.55}>
              <p className="text-xs text-neutral-500 mb-2">Artigos do PubMed ligados aos compostos (amostra de 100)</p>
              {loadingArticles ? (
                <Loader label="Carregando artigos..." />
              ) : articlesByYear.length === 0 ? (
                <p className="text-sm text-neutral-500 text-center py-8">Sem artigos com ano.</p>
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={articlesByYear} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                    <XAxis dataKey="year" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" />
                    <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" allowDecimals={false} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Line
                      type="monotone" dataKey="count" stroke={COLORS.teal} strokeWidth={2}
                      dot={{ r: 3, fill: COLORS.teal }} activeDot={{ r: 5 }}
                      name="Artigos"
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Section>
          </div>
        </>
      )}

      {/* Nota metodológica */}
      <Section title="Notas metodológicas" delay={0.6}>
        <div className="grid gap-3 lg:grid-cols-2 text-xs text-neutral-600">
          <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={12} className="text-amber-600" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-700">Amostragem</span>
            </div>
            <p>
              Os gráficos derivados de compostos usam <strong>até 100 itens</strong> por consulta (limite do endpoint
              <code className="mx-1 px-1.5 py-0.5 rounded bg-white border border-gray-200 font-mono text-[10px]">/compounds</code>).
              Para análise sobre o banco inteiro, use o dashboard Streamlit ou consultas SQL diretas.
            </p>
          </div>
          <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Crosshair size={12} className="text-violet-600" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-700">Top targets</span>
            </div>
            <p>
              Ordenado por <code className="mx-1 px-1.5 py-0.5 rounded bg-white border border-gray-200 font-mono text-[10px]">compounds_tested</code> em todo o banco —
              é independente dos filtros de compostos. Para alvos específicos de uma fatia, use a página Targets.
            </p>
          </div>
        </div>
      </Section>
    </div>
  )
}
