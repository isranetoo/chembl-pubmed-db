import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Microscope, Activity, Layers, Database, Search, ArrowUpRight,
  Image as ImageIcon,
} from 'lucide-react'
import {
  useHistopathStats, useHistopathSummary, useHistopathCohorts,
} from '../lib/hooks'
import { formatNumber } from '../lib/utils'
import Section from '../components/Section'
import Loader from '../components/Loader'
import StatCard from '../components/StatCard'
import EmptyState from '../components/EmptyState'

// Mapeamento das colunas-resumo da view v_tme_summary → UI legíveis
const SUMMARY_FEATURES = [
  { key: 'tils_diffusivity_mean',     label: 'TILs diffusivity',      desc: 'Penetração de linfócitos T no tumor' },
  { key: 'lymphocyte_density_mean',   label: 'Linfócitos',            desc: 'Densidade global de linfócitos' },
  { key: 'fibroblast_density_mean',   label: 'Fibroblastos',          desc: 'Componente estromal' },
  { key: 'cancer_cell_density_mean',  label: 'Células tumorais',      desc: 'Densidade de células cancerosas' },
  { key: 'neutrophil_density_mean',   label: 'Neutrófilos',           desc: 'Marcador de inflamação aguda' },
  { key: 'tils_in_tumor_mean',        label: 'TILs no tumor',         desc: 'Linfócitos dentro da massa tumoral' },
]

// Calcula min/max por feature pra normalizar barras
function buildScales(rows, keys) {
  const scales = {}
  keys.forEach((k) => {
    const vals = rows.map((r) => r[k]).filter((v) => v != null && Number.isFinite(v))
    if (vals.length === 0) {
      scales[k] = { min: 0, max: 1 }
    } else {
      scales[k] = { min: Math.min(...vals), max: Math.max(...vals) }
    }
  })
  return scales
}

function normalize(value, scale) {
  if (value == null || !Number.isFinite(value)) return null
  const { min, max } = scale
  if (max === min) return 0.5
  return (value - min) / (max - min)
}

function MiniBar({ value, scale, color = 'green' }) {
  const n = normalize(value, scale)
  if (n == null) return <span className="text-gray-300 text-[10px]">—</span>
  const pct = Math.max(2, Math.min(100, n * 100))
  const colorMap = {
    green: 'from-green-500 to-green-700',
    sky:   'from-sky-500 to-sky-700',
    amber: 'from-amber-500 to-amber-700',
    rose:  'from-rose-500 to-rose-700',
    violet:'from-violet-500 to-violet-700',
    teal:  'from-teal-500 to-teal-700',
  }
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-12 h-1.5 rounded-full bg-gray-100 overflow-hidden">
        <div className={`h-full rounded-full bg-gradient-to-r ${colorMap[color] || colorMap.green}`}
          style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-mono text-gray-600 w-14 text-right">
        {value < 1 ? value.toFixed(3) : value.toFixed(1)}
      </span>
    </div>
  )
}

export default function HistopathologyPage() {
  const [q, setQ] = useState('')

  const statsQ    = useHistopathStats()
  const summaryQ  = useHistopathSummary()
  const cohortsQ  = useHistopathCohorts()

  // Junta dicionário + summary, filtra por busca
  const rows = useMemo(() => {
    const dict = cohortsQ.data?.cohorts || []
    const summary = summaryQ.data?.summary || []
    const sumByCohort = Object.fromEntries(summary.map((s) => [s.tcga_cohort, s]))
    const merged = dict.map((c) => ({
      ...c,
      ...(sumByCohort[c.tcga_cohort] || {}),
      has_data: Boolean(sumByCohort[c.tcga_cohort]),
    }))
    const query = q.trim().toLowerCase()
    if (!query) return merged
    return merged.filter((c) =>
      c.tcga_cohort.toLowerCase().includes(query) ||
      c.cancer_name.toLowerCase().includes(query)
    )
  }, [cohortsQ.data, summaryQ.data, q])

  const scales = useMemo(
    () => buildScales(rows, SUMMARY_FEATURES.map((f) => f.key)),
    [rows],
  )

  const loading = statsQ.isLoading || cohortsQ.isLoading || summaryQ.isLoading

  if (loading) return <Loader label="Carregando dados Owkin..." />
  if (statsQ.error || cohortsQ.error) return (
    <div className="bg-white border border-rose-300 rounded-xl p-5 text-rose-700 text-sm">
      {statsQ.error?.message || cohortsQ.error?.message}
    </div>
  )

  const stats = statsQ.data || {}
  const withData = rows.filter((r) => r.has_data).length

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-rose-700 mb-2">Histopatologia</p>
        <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-gray-800">
          Microambiente <span className="bg-gradient-to-br from-green-600 to-green-900 text-transparent bg-clip-text">Tumoral (TME)</span>
        </h1>
        <p className="mt-2 text-sm text-neutral-600 max-w-2xl">
          Features histômicas extraídas pela Owkin sobre lâminas TCGA — densidades celulares (TILs, fibroblastos,
          células tumorais), diffusivity de linfócitos, áreas e co-ocorrências espaciais.
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Coortes TCGA" value={cohortsQ.data?.total ?? 0} icon={Microscope} color="rose" delay={0.05}
          helper={`${withData} com dados TME cacheados`} />
        <StatCard label="Indicações mapeadas" value={stats.total_mappings} icon={Database} color="sky" delay={0.1}
          helper={`${stats.mapped_cohorts} coortes alcançadas`} />
        <StatCard label="Features cacheadas" value={stats.cached_features} icon={Activity} color="emerald" delay={0.15}
          helper="mean/std/quartis por coorte" />
        <StatCard label="Slides indexadas" value={stats.cached_slides} icon={ImageIcon} color="violet" delay={0.2}
          helper="top-ranked por feature" />
      </div>

      {/* Filtro */}
      <Section title="Comparativo entre coortes" delay={0.25}>
        <div className="flex items-center gap-2 mb-3">
          <div className="relative flex-1 max-w-md">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className="glass-input w-full pl-9"
              placeholder="Buscar por sigla (BRCA, LUAD…) ou nome do câncer"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <span className="text-[11px] text-neutral-500">{rows.length} coortes</span>
        </div>

        <p className="text-[11px] text-neutral-500 mb-3">
          Cada barra é normalizada por feature (min–max das coortes visíveis) — permite enxergar quais
          coortes são "frias" (poucos TILs) vs "quentes" imunologicamente. Click numa coorte pra abrir detalhe.
        </p>

        {rows.length === 0 ? <EmptyState /> : (
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-3 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Coorte</th>
                  <th className="text-left px-3 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Câncer</th>
                  {SUMMARY_FEATURES.map((f) => (
                    <th key={f.key} className="text-left px-3 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold"
                        title={f.desc}>
                      {f.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map((row) => (
                  <tr key={row.tcga_cohort} className="hover:bg-rose-50/40 transition-colors">
                    <td className="px-3 py-3">
                      <Link to={`/histopathology/${row.tcga_cohort}`}
                        className="group inline-flex items-center gap-1.5">
                        <code className="text-[11px] font-mono font-semibold text-rose-800 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded">
                          {row.tcga_cohort}
                        </code>
                        <ArrowUpRight size={11} className="opacity-0 group-hover:opacity-100 transition-opacity text-rose-700" />
                      </Link>
                    </td>
                    <td className="px-3 py-3">
                      <Link to={`/histopathology/${row.tcga_cohort}`}
                        className="text-xs text-gray-800 font-medium hover:text-rose-700 transition-colors">
                        {row.cancer_name}
                      </Link>
                      {!row.has_data && (
                        <span className="ml-2 text-[9px] uppercase tracking-wider text-amber-700">sem cache</span>
                      )}
                    </td>
                    {SUMMARY_FEATURES.map((f, i) => {
                      const colors = ['green', 'sky', 'amber', 'rose', 'violet', 'teal']
                      return (
                        <td key={f.key} className="px-3 py-3">
                          <MiniBar value={row[f.key]} scale={scales[f.key]} color={colors[i % colors.length]} />
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* Legenda */}
      <Section title="Sobre os dados" delay={0.3}>
        <div className="grid gap-3 lg:grid-cols-2 text-xs text-neutral-600">
          <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-700 mb-2">Fonte</p>
            <p>
              <strong>Owkin Pathology Explorer</strong> — features automaticamente extraídas de WSIs (whole slide images)
              do <strong>TCGA</strong> por modelos de visão treinados pela Owkin. Cobertura: 26 tipos tumorais, ~56 features
              quantitativas por slide.
            </p>
          </div>
          <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-700 mb-2">Por que isto importa</p>
            <p>
              TILs (linfócitos infiltrando tumor) preveem resposta a imunoterapia. Densidade de fibroblastos
              correlaciona com resistência. Comparar perfis TME entre coortes ajuda a entender o nicho onde o
              composto será usado.
            </p>
          </div>
        </div>
      </Section>
    </div>
  )
}
