import { useMemo, useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, Microscope, ImageIcon, Activity, Tag, ChevronDown,
} from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
  ComposedChart, Line, Area,
} from 'recharts'
import {
  useHistopathCohorts, useCohortTme, useCohortSlides, useHistopathFeatures,
} from '../lib/hooks'
import { formatNumber } from '../lib/utils'
import Section from '../components/Section'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import Pill from '../components/Pill'

const TOOLTIP_STYLE = {
  backgroundColor: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: 12,
  fontSize: 12,
  fontFamily: 'Kanit',
  color: '#1f2937',
  boxShadow: '0 4px 14px rgba(33,81,83,0.08)',
}

// Agrupamento das features pra organizar a UI
const FEATURE_GROUPS = [
  {
    label: 'Células tumorais',
    color: 'rose',
    match: (f) => f.includes('cancer_cell'),
  },
  {
    label: 'Linfócitos / TILs',
    color: 'green',
    match: (f) => f.includes('lymphocyt') || f.includes('tils'),
  },
  {
    label: 'Fibroblastos / Estroma',
    color: 'amber',
    match: (f) => f.includes('fibroblast') || f.includes('stroma'),
  },
  {
    label: 'Inflamação',
    color: 'sky',
    match: (f) => f.includes('neutrophil') || f.includes('eosinoph') || f.includes('plasmocyt'),
  },
  {
    label: 'Áreas / Co-ocorrência',
    color: 'violet',
    match: (f) => f.includes('area') || f.includes('co_occurrence'),
  },
]

function groupFor(feature) {
  return FEATURE_GROUPS.find((g) => g.match(feature)) || { label: 'Outras', color: 'slate' }
}

function shortFeature(f) {
  return f.replace(/_/g, ' ').replace(/rad ([0-9.]+)um/, 'r=$1µm')
}

const COLOR_HEX = {
  rose:   '#be185d',
  green:  '#2f6b14',
  amber:  '#b45309',
  sky:    '#0369a1',
  violet: '#7c3aed',
  slate:  '#64748b',
}

export default function HistopathologyCohortPage() {
  const { cohort } = useParams()
  const cohortUp = (cohort || '').toUpperCase()
  const [selectedFeature, setSelectedFeature] = useState('tils_diffusivity')

  const cohortsQ  = useHistopathCohorts()
  const tmeQ      = useCohortTme(cohortUp)
  const slidesQ   = useCohortSlides(cohortUp, { feature: selectedFeature, limit: 20 })

  const dict = useMemo(
    () => (cohortsQ.data?.cohorts || []).find((c) => c.tcga_cohort === cohortUp),
    [cohortsQ.data, cohortUp],
  )

  // Garante que o feature selecionado existe no cache; senão, troca pro 1º
  useEffect(() => {
    const features = (tmeQ.data?.stats || []).map((s) => s.feature)
    if (features.length === 0) return
    if (!features.includes(selectedFeature)) {
      setSelectedFeature(features[0])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tmeQ.data])

  // Stats agrupados
  const grouped = useMemo(() => {
    const stats = tmeQ.data?.stats || []
    const groups = FEATURE_GROUPS.map((g) => ({ ...g, items: [] }))
    const other = { label: 'Outras', color: 'slate', items: [] }
    stats.forEach((s) => {
      const g = FEATURE_GROUPS.findIndex((gg) => gg.match(s.feature))
      if (g >= 0) groups[g].items.push(s)
      else other.items.push(s)
    })
    return [...groups, other].filter((g) => g.items.length > 0)
  }, [tmeQ.data])

  // Histograma "boxplot lite" — usa quartis pra desenhar área + linha
  const selectedStat = useMemo(
    () => (tmeQ.data?.stats || []).find((s) => s.feature === selectedFeature),
    [tmeQ.data, selectedFeature],
  )
  const quartileChart = useMemo(() => {
    if (!selectedStat) return []
    const { min, p25, p50, p75, max, mean } = selectedStat
    return [
      { quantile: 'min', value: min },
      { quantile: 'p25', value: p25, box: p25 },
      { quantile: 'p50', value: p50, box: p50, median: p50 },
      { quantile: 'p75', value: p75, box: p75 },
      { quantile: 'max', value: max },
    ].map((r) => ({ ...r, mean }))
  }, [selectedStat])

  if (cohortsQ.isLoading || tmeQ.isLoading) return <Loader label="Carregando dados da coorte..." />
  if (tmeQ.error) return (
    <div className="bg-white border border-rose-300 rounded-xl p-5 text-rose-700 text-sm">{tmeQ.error.message}</div>
  )

  const cancerName = dict?.cancer_name || cohortUp
  const keywords   = dict?.keywords || []
  const stats      = tmeQ.data?.stats || []

  return (
    <div className="space-y-6 pb-8">
      <Link to="/histopathology" className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-rose-700 transition-colors">
        <ArrowLeft size={12} /> Voltar para Histopatologia
      </Link>

      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-2xl shadow-card p-6 animate-fade-in-up">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-rose-700 mb-2">Coorte TCGA</p>
            <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-gray-800 mb-2">
              {cancerName}
            </h1>
            <div className="flex flex-wrap items-center gap-2">
              <code className="text-xs text-rose-800 font-mono bg-rose-50 border border-rose-200 px-2 py-0.5 rounded font-semibold">
                {cohortUp}
              </code>
              <Pill className="bg-gray-100 text-gray-700 border-gray-200">{stats.length} features cacheadas</Pill>
            </div>
            {keywords.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 mt-3">
                <Tag size={11} className="text-gray-400" />
                {keywords.map((k) => (
                  <span key={k} className="px-2 py-0.5 rounded-md bg-gray-50 border border-gray-200 text-[10px] text-gray-600">
                    {k}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-rose-500 to-rose-700 shadow-md flex-shrink-0">
            <Microscope size={36} className="text-white" />
          </div>
        </div>
      </div>

      {stats.length === 0 ? (
        <div className="bg-white border border-amber-300 rounded-2xl p-8 text-center">
          <Microscope size={28} className="mx-auto text-amber-500 mb-2" />
          <p className="text-sm text-amber-800 font-medium">Sem dados TME cacheados para esta coorte.</p>
          <p className="text-xs text-amber-700 mt-1">
            Rode o pipeline Owkin pra popular <code className="font-mono">owkin_cohort_stats</code> e <code className="font-mono">owkin_slides</code>.
          </p>
        </div>
      ) : (
        <>
          {/* Feature picker + distribuição */}
          <Section title="Distribuição por feature">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Feature:</span>
              <div className="relative">
                <select
                  className="glass-input pr-9 appearance-none"
                  value={selectedFeature}
                  onChange={(e) => setSelectedFeature(e.target.value)}
                >
                  {grouped.flatMap((g) =>
                    g.items.map((s) => (
                      <option key={s.feature} value={s.feature}>
                        [{g.label}] {shortFeature(s.feature)}
                      </option>
                    ))
                  )}
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
            </div>

            {selectedStat && (
              <>
                <div className="grid gap-3 grid-cols-2 lg:grid-cols-5 mb-4">
                  {[
                    { label: 'Mean', value: selectedStat.mean },
                    { label: 'Std',  value: selectedStat.std },
                    { label: 'P25',  value: selectedStat.p25 },
                    { label: 'Median', value: selectedStat.p50 },
                    { label: 'P75',  value: selectedStat.p75 },
                  ].map((m) => (
                    <div key={m.label} className="rounded-lg bg-gray-50 border border-gray-200 p-3">
                      <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">{m.label}</p>
                      <p className="text-base font-bold text-gray-800 font-mono mt-1">
                        {m.value != null ? Number(m.value).toFixed(3) : '—'}
                      </p>
                    </div>
                  ))}
                </div>

                <ResponsiveContainer width="100%" height={240}>
                  <ComposedChart data={quartileChart} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
                    <XAxis dataKey="quantile" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" />
                    <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" />
                    <Tooltip contentStyle={TOOLTIP_STYLE}
                      formatter={(v, n) => [Number(v).toFixed(4), n]} />
                    <Area type="monotone" dataKey="box" fill="#be185d" fillOpacity={0.15} stroke="none" />
                    <Line type="monotone" dataKey="value" stroke="#be185d" strokeWidth={2}
                      dot={{ r: 4, fill: '#be185d' }} name="Valor" />
                    <Line type="monotone" dataKey="mean" stroke="#0d9488" strokeDasharray="6 4"
                      strokeWidth={1.5} dot={false} name="Mean (ref)" />
                  </ComposedChart>
                </ResponsiveContainer>
                <p className="text-[10px] text-gray-400 text-center mt-1">
                  Min → P25 → Mediana → P75 → Max (linha tracejada teal = média)
                </p>
              </>
            )}
          </Section>

          {/* Top slides */}
          <Section title="Top slides ranqueados">
            <p className="text-xs text-neutral-500 mb-3">
              Slides com maior valor da feature selecionada. Slide IDs podem ser consultados no Owkin Pathology Explorer.
            </p>
            {slidesQ.isLoading ? <Loader label="Carregando slides..." /> :
             !slidesQ.data?.slides?.length ? (
              <p className="text-sm text-neutral-500 py-4 text-center">Sem slides cacheadas para esta feature.</p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Rank</th>
                      <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Slide ID</th>
                      <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Valor</th>
                      <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Coletado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {slidesQ.data.slides.map((s) => (
                      <tr key={s.slide_id} className="hover:bg-rose-50/40 transition-colors">
                        <td className="px-4 py-2.5">
                          <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-rose-100 text-rose-700 text-xs font-bold">
                            #{s.rank}
                          </span>
                        </td>
                        <td className="px-4 py-2.5">
                          <code className="text-xs text-gray-800 font-mono">{s.slide_id}</code>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="font-mono text-xs text-gray-700">{Number(s.value).toFixed(4)}</span>
                        </td>
                        <td className="px-4 py-2.5 text-[11px] text-gray-500">{s.fetched_at?.slice(0, 10)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          {/* Todas as features agrupadas */}
          <Section title="Todas as features TME">
            <p className="text-xs text-neutral-500 mb-3">
              {stats.length} features agrupadas por categoria biológica. Clique em uma feature pra usar como ranking dos slides acima.
            </p>
            <div className="space-y-4">
              {grouped.map((g) => (
                <div key={g.label}>
                  <p className="text-[11px] font-semibold uppercase tracking-wider mb-2"
                     style={{ color: COLOR_HEX[g.color] }}>
                    {g.label} · {g.items.length}
                  </p>
                  <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
                    <table className="min-w-full text-xs">
                      <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                          <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Feature</th>
                          <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Mean ± Std</th>
                          <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">P25</th>
                          <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">P50</th>
                          <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">P75</th>
                          <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Range</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {g.items.map((s) => {
                          const isActive = s.feature === selectedFeature
                          return (
                            <tr key={s.feature}
                              onClick={() => setSelectedFeature(s.feature)}
                              className={`cursor-pointer transition-colors ${
                                isActive ? 'bg-rose-50' : 'hover:bg-gray-50'
                              }`}>
                              <td className="px-3 py-2 font-mono text-gray-700">
                                {isActive && <span className="text-rose-600 mr-1">▸</span>}
                                {shortFeature(s.feature)}
                              </td>
                              <td className="px-3 py-2 font-mono text-right text-gray-700">
                                {s.mean != null ? Number(s.mean).toFixed(3) : '—'}
                                <span className="text-gray-400"> ± {s.std != null ? Number(s.std).toFixed(2) : '—'}</span>
                              </td>
                              <td className="px-3 py-2 font-mono text-right text-gray-600">{s.p25 != null ? Number(s.p25).toFixed(3) : '—'}</td>
                              <td className="px-3 py-2 font-mono text-right text-gray-600">{s.p50 != null ? Number(s.p50).toFixed(3) : '—'}</td>
                              <td className="px-3 py-2 font-mono text-right text-gray-600">{s.p75 != null ? Number(s.p75).toFixed(3) : '—'}</td>
                              <td className="px-3 py-2 font-mono text-right text-gray-500">
                                {s.min != null ? Number(s.min).toFixed(2) : '—'} — {s.max != null ? Number(s.max).toFixed(2) : '—'}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        </>
      )}
    </div>
  )
}
