import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueries } from '@tanstack/react-query'
import { api } from '../lib/api'
import { formatNumber, phaseLabel, getPhaseColor } from '../lib/utils'
import Section from '../components/Section'
import Loader from '../components/Loader'
import EmptyState from '../components/EmptyState'
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, BarChart, Bar, Cell, ReferenceLine, LabelList,
} from 'recharts'
import {
  Plus, X, Search, FlaskConical, Atom, GitCompareArrows, CheckCircle,
  XCircle, TrendingUp, Beaker, ArrowRight,
} from 'lucide-react'

// ── Color palette for compounds ──────────────────────────────
const COLORS = [
  { main: '#34d399', light: 'rgba(52,211,153,0.15)', name: 'emerald' },
  { main: '#60a5fa', light: 'rgba(96,165,250,0.15)', name: 'blue' },
  { main: '#f472b6', light: 'rgba(244,114,182,0.15)', name: 'pink' },
  { main: '#fbbf24', light: 'rgba(251,191,36,0.15)', name: 'amber' },
]

const CHEMBL_IMG = (id) => `https://www.ebi.ac.uk/chembl/api/data/image/${id}.svg`

// ── Compound search/selector ─────────────────────────────────
function CompoundSelector({ selected, onAdd, onRemove }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const { data } = useQuery({
    queryKey: ['compounds-search', query],
    queryFn: () => api.getCompounds({ q: query || undefined, size: 12 }),
    enabled: query.length > 0,
    staleTime: 10_000,
  })

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const results = (data?.items || []).filter(
    (c) => !selected.find((s) => s.chembl_id === c.chembl_id)
  )

  return (
    <div className="space-y-4">
      {/* Selected chips */}
      <div className="flex flex-wrap gap-2">
        {selected.map((c, i) => (
          <div key={c.chembl_id}
            className="flex items-center gap-2 rounded-xl px-3 py-2 border transition-all"
            style={{
              backgroundColor: COLORS[i]?.light || 'rgba(255,255,255,0.05)',
              borderColor: COLORS[i]?.main + '33' || 'rgba(255,255,255,0.1)',
            }}>
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i]?.main }} />
            <span className="text-sm font-medium text-white/80">{c.name}</span>
            <span className="text-[10px] font-mono text-white/30">{c.chembl_id}</span>
            <button onClick={() => onRemove(c.chembl_id)}
              className="ml-1 p-0.5 rounded-md hover:bg-white/10 transition-colors">
              <X size={12} className="text-white/40" />
            </button>
          </div>
        ))}
        {selected.length === 0 && (
          <p className="text-sm text-white/25 py-2">Nenhum composto selecionado. Use a busca abaixo.</p>
        )}
      </div>

      {/* Search input */}
      {selected.length < 4 && (
        <div className="relative" ref={ref}>
          <div className="relative">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/25" />
            <input
              className="glass-input w-full pl-10"
              placeholder={`Adicionar composto (${selected.length}/4)...`}
              value={query}
              onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
              onFocus={() => query && setOpen(true)}
            />
          </div>

          {open && results.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-2 z-50 rounded-xl bg-slate-900/95 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/40 max-h-64 overflow-y-auto">
              {results.map((c) => (
                <button key={c.chembl_id}
                  onClick={() => { onAdd(c); setQuery(''); setOpen(false) }}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.06] transition-colors border-b border-white/[0.04] last:border-0">
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                    <FlaskConical size={13} className="text-emerald-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white/80 truncate">{c.name || c.chembl_id}</p>
                    <p className="text-[11px] text-white/30 font-mono">{c.chembl_id}</p>
                  </div>
                  <Plus size={14} className="text-white/20 flex-shrink-0" />
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Molecular structure viewer ───────────────────────────────
function MoleculeCard({ compound, color, index }) {
  const [imgError, setImgError] = useState(false)

  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4 text-center animate-fade-in-up"
      style={{ animationDelay: `${index * 0.1}s` }}>
      <div className="w-full aspect-square rounded-lg bg-white/[0.02] border border-white/[0.04] mb-3 flex items-center justify-center overflow-hidden">
        {!imgError ? (
          <img
            src={CHEMBL_IMG(compound.chembl_id)}
            alt={`Estrutura de ${compound.name}`}
            className="w-full h-full object-contain p-3 invert opacity-80"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-white/20">
            <Atom size={32} />
            <span className="text-[10px]">Sem imagem</span>
          </div>
        )}
      </div>
      <div className="flex items-center justify-center gap-2 mb-1">
        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color.main }} />
        <h4 className="text-sm font-semibold text-white/85" style={{ fontFamily: 'Outfit' }}>
          {compound.name}
        </h4>
      </div>
      <p className="text-[11px] font-mono text-white/30">{compound.chembl_id}</p>
      {compound.molecular_formula && (
        <p className="text-[11px] text-white/20 mt-1">{compound.molecular_formula}</p>
      )}
    </div>
  )
}

// ── ADMET Radar Chart ────────────────────────────────────────
function AdmetRadar({ admetData, compounds }) {
  if (!admetData || admetData.length === 0) return null

  // Normalize values to 0-1 for radar display
  const normalize = (val, max) => val != null ? Math.min(Math.max(val / max, 0), 1) : 0

  const radarData = [
    { prop: 'QED', fullMark: 1 },
    { prop: 'Lipofilia', fullMark: 1 },
    { prop: 'Polaridade', fullMark: 1 },
    { prop: 'HBD', fullMark: 1 },
    { prop: 'HBA', fullMark: 1 },
    { prop: 'Flexibilidade', fullMark: 1 },
  ].map((item) => {
    const row = { ...item }
    admetData.forEach((admet, i) => {
      if (!admet) return
      const key = compounds[i].chembl_id
      switch (item.prop) {
        case 'QED': row[key] = normalize(admet.qed_weighted, 1); break
        case 'Lipofilia': row[key] = Math.max(0, 1 - normalize(Math.abs(admet.alogp || 0), 7)); break
        case 'Polaridade': row[key] = Math.max(0, 1 - normalize(admet.psa || 0, 200)); break
        case 'HBD': row[key] = Math.max(0, 1 - normalize(admet.hbd || 0, 7)); break
        case 'HBA': row[key] = Math.max(0, 1 - normalize(admet.hba || 0, 15)); break
        case 'Flexibilidade': row[key] = Math.max(0, 1 - normalize(admet.rtb || 0, 15)); break
      }
    })
    return row
  })

  return (
    <ResponsiveContainer width="100%" height={340}>
      <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="rgba(255,255,255,0.06)" />
        <PolarAngleAxis
          dataKey="prop"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'Outfit' }}
        />
        <PolarRadiusAxis
          angle={30} domain={[0, 1]}
          tick={{ fill: 'rgba(255,255,255,0.15)', fontSize: 9 }}
          axisLine={false}
        />
        {compounds.map((c, i) => (
          <Radar
            key={c.chembl_id}
            name={c.name}
            dataKey={c.chembl_id}
            stroke={COLORS[i].main}
            fill={COLORS[i].main}
            fillOpacity={0.12}
            strokeWidth={2}
            dot={{ r: 3, fill: COLORS[i].main }}
          />
        ))}
        <Legend
          wrapperStyle={{ fontSize: 11, fontFamily: 'Outfit', color: 'rgba(255,255,255,0.5)' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(15,23,42,0.95)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 12, fontSize: 12, fontFamily: 'DM Sans',
          }}
          formatter={(v) => [(v * 100).toFixed(0) + '%']}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}

// ── Scatter: ALogP × PSA ─────────────────────────────────────
function DruglikenessScatter({ admetData, compounds }) {
  if (!admetData || admetData.length === 0) return null

  const scatterSeries = compounds.map((c, i) => ({
    name: c.name,
    data: admetData[i] ? [{
      x: admetData[i].alogp ?? 0,
      y: admetData[i].psa ?? 0,
      qed: admetData[i].qed_weighted ?? 0,
      name: c.name,
    }] : [],
    color: COLORS[i].main,
  })).filter(s => s.data.length > 0)

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis
          type="number" dataKey="x" name="ALogP"
          label={{ value: 'ALogP', position: 'bottom', offset: 0, style: { fill: 'rgba(255,255,255,0.35)', fontSize: 11 } }}
          tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
          stroke="rgba(255,255,255,0.06)"
        />
        <YAxis
          type="number" dataKey="y" name="PSA"
          label={{ value: 'PSA (Å²)', angle: -90, position: 'insideLeft', style: { fill: 'rgba(255,255,255,0.35)', fontSize: 11 } }}
          tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
          stroke="rgba(255,255,255,0.06)"
        />
        <ReferenceLine x={5} stroke="rgba(251,191,36,0.3)" strokeDasharray="6 4" label={{ value: 'Lipinski (ALogP=5)', position: 'top', style: { fill: 'rgba(251,191,36,0.5)', fontSize: 9 } }} />
        <ReferenceLine y={140} stroke="rgba(244,114,182,0.3)" strokeDasharray="6 4" label={{ value: 'Veber (PSA=140)', position: 'right', style: { fill: 'rgba(244,114,182,0.5)', fontSize: 9 } }} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(15,23,42,0.95)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 12, fontSize: 12,
          }}
          formatter={(v, name) => [typeof v === 'number' ? v.toFixed(2) : v, name]}
          labelFormatter={(l) => ''}
        />
        <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'Outfit' }} />
        {scatterSeries.map((s) => (
          <Scatter key={s.name} name={s.name} data={s.data} fill={s.color} stroke={s.color} strokeWidth={2} r={8}>
            {s.data.map((_, idx) => (
              <Cell key={idx} fill={s.color} fillOpacity={0.7} />
            ))}
          </Scatter>
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  )
}

// ── Indications bar chart ────────────────────────────────────
function IndicationsChart({ indicationsData, compounds }) {
  if (!indicationsData || indicationsData.length === 0) return null

  const phases = [4, 3, 2, 1]
  const barData = phases.map((phase) => {
    const row = { phase: phaseLabel(phase) }
    compounds.forEach((c, i) => {
      const inds = indicationsData[i]?.items || []
      row[c.chembl_id] = inds.filter((ind) => Number(ind.max_phase) === phase).length
    })
    return row
  }).filter((row) => {
    return compounds.some((c) => row[c.chembl_id] > 0)
  })

  if (barData.length === 0) return <p className="text-sm text-white/25 text-center py-8">Sem indicações para comparar.</p>

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={barData} margin={{ top: 10, right: 10, bottom: 5, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="phase" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} stroke="rgba(255,255,255,0.06)" />
        <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} stroke="rgba(255,255,255,0.06)" allowDecimals={false} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'rgba(15,23,42,0.95)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 12, fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'Outfit' }} />
        {compounds.map((c, i) => (
          <Bar key={c.chembl_id} dataKey={c.chembl_id} name={c.name}
            fill={COLORS[i].main} fillOpacity={0.7} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Comparative table ────────────────────────────────────────
function CompareTable({ admetData, compounds }) {
  if (!admetData || admetData.length === 0) return null

  const goodRange = (val, min, max) => {
    if (val == null) return 'neutral'
    return val >= min && val <= max ? 'good' : 'bad'
  }

  const properties = [
    { key: 'qed_weighted', label: 'QED (Drug-likeness)', fmt: 4, eval: (v) => goodRange(v, 0.5, 1) },
    { key: 'alogp', label: 'ALogP (Lipofilia)', fmt: 2, eval: (v) => goodRange(v, -0.4, 5) },
    { key: 'psa', label: 'PSA (Å²)', fmt: 1, eval: (v) => goodRange(v, 0, 140) },
    { key: 'mw_freebase', label: 'MW (Da)', fmt: 1, eval: (v) => goodRange(v, 0, 500) },
    { key: 'hbd', label: 'H-Bond Donors', fmt: 0, eval: (v) => goodRange(v, 0, 5) },
    { key: 'hba', label: 'H-Bond Acceptors', fmt: 0, eval: (v) => goodRange(v, 0, 10) },
    { key: 'rtb', label: 'Rotatable Bonds', fmt: 0, eval: (v) => goodRange(v, 0, 10) },
    { key: 'aromatic_rings', label: 'Anéis Aromáticos', fmt: 0, eval: () => 'neutral' },
    { key: 'heavy_atoms', label: 'Heavy Atoms', fmt: 0, eval: () => 'neutral' },
    { key: 'num_ro5_violations', label: 'Ro5 Violações', fmt: 0, eval: (v) => v === 0 ? 'good' : 'bad' },
    { key: 'num_alerts', label: 'Alertas PAINS', fmt: 0, eval: (v) => v === 0 ? 'good' : 'bad' },
    { key: 'lipinski_pass', label: 'Lipinski', fmt: 'bool', eval: (v) => v ? 'good' : 'bad' },
    { key: 'veber_pass', label: 'Veber', fmt: 'bool', eval: (v) => v ? 'good' : 'bad' },
    { key: 'pains_free', label: 'PAINS Free', fmt: 'bool', eval: (v) => v ? 'good' : 'bad' },
  ]

  const cellColor = {
    good: 'bg-emerald-500/10 text-emerald-300',
    bad: 'bg-red-500/10 text-red-300',
    neutral: 'text-white/60',
  }

  const formatVal = (val, fmt) => {
    if (val == null) return '—'
    if (fmt === 'bool') return val ? '✓' : '✗'
    return Number(val).toFixed(fmt)
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-white/[0.06]">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-white/[0.03] border-b border-white/[0.06]">
            <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider text-white/40 font-medium">Propriedade</th>
            {compounds.map((c, i) => (
              <th key={c.chembl_id} className="text-center px-4 py-3">
                <div className="flex items-center justify-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i].main }} />
                  <span className="text-[11px] uppercase tracking-wider text-white/60 font-semibold">{c.name}</span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.04]">
          {properties.map((prop) => (
            <tr key={prop.key} className="hover:bg-white/[0.02] transition-colors">
              <td className="px-4 py-3 text-xs text-white/50 font-medium">{prop.label}</td>
              {compounds.map((c, i) => {
                const val = admetData[i]?.[prop.key]
                const status = prop.eval(val)
                return (
                  <td key={c.chembl_id} className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center justify-center rounded-lg px-3 py-1 text-xs font-mono font-medium ${cellColor[status]}`}>
                      {formatVal(val, prop.fmt)}
                    </span>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═════════════════════════════════════════════════════════════

export default function ComparePage() {
  const [selected, setSelected] = useState([])

  const handleAdd = (compound) => {
    if (selected.length < 4 && !selected.find((s) => s.chembl_id === compound.chembl_id)) {
      setSelected([...selected, compound])
    }
  }

  const handleRemove = (chemblId) => {
    setSelected(selected.filter((s) => s.chembl_id !== chemblId))
  }

  // Parallel queries for ADMET data
  const admetQueries = useQueries({
    queries: selected.map((c) => ({
      queryKey: ['compound-admet', c.chembl_id],
      queryFn: () => api.getCompoundAdmet(c.chembl_id),
      enabled: true,
      staleTime: 60_000,
    })),
  })

  // Parallel queries for indications
  const indicationQueries = useQueries({
    queries: selected.map((c) => ({
      queryKey: ['compound-indications', c.chembl_id, { size: 100 }],
      queryFn: () => api.getCompoundIndications(c.chembl_id, { size: 100 }),
      enabled: true,
      staleTime: 60_000,
    })),
  })

  const allAdmetLoaded = admetQueries.every((q) => !q.isLoading)
  const allIndicationsLoaded = indicationQueries.every((q) => !q.isLoading)
  const admetData = admetQueries.map((q) => q.data || null)
  const indicationsData = indicationQueries.map((q) => q.data || null)

  const hasData = selected.length >= 2

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-pink-400/60 mb-2">Compare</p>
        <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit' }}>
          Comparar Compostos
        </h1>
        <p className="mt-2 text-sm text-white/35">
          Selecione 2 a 4 compostos para comparar propriedades ADMET, indicações e estrutura molecular.
        </p>
      </div>

      {/* Selector */}
      <Section title="Selecionar compostos" delay={0.05}>
        <CompoundSelector selected={selected} onAdd={handleAdd} onRemove={handleRemove} />
      </Section>

      {/* Empty state */}
      {!hasData && (
        <div className="glass-card p-12 text-center animate-fade-in">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-pink-500/10 to-violet-500/10 border border-white/[0.06] flex items-center justify-center mx-auto mb-4">
            <GitCompareArrows size={28} className="text-white/15" />
          </div>
          <h3 className="text-lg font-semibold text-white/60 mb-2" style={{ fontFamily: 'Outfit' }}>
            {selected.length === 0 ? 'Selecione compostos para comparar' : 'Adicione mais um composto'}
          </h3>
          <p className="text-sm text-white/25 max-w-md mx-auto">
            {selected.length === 0
              ? 'Busque e adicione entre 2 e 4 compostos para ver o radar ADMET, scatter de druglikeness, tabela comparativa e estruturas moleculares.'
              : 'Você precisa de pelo menos 2 compostos para iniciar a comparação.'
            }
          </p>
          {selected.length === 0 && (
            <div className="flex flex-wrap justify-center gap-2 mt-6">
              {['Aspirin', 'Ibuprofen', 'Metformin'].map((name) => (
                <span key={name} className="px-3 py-1.5 rounded-lg text-xs text-white/25 bg-white/[0.03] border border-white/[0.06]">
                  ex: {name}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Comparison content */}
      {hasData && (
        <>
          {/* Molecular structures */}
          <Section title="Estrutura Molecular" delay={0.1}>
            <p className="text-xs text-white/25 mb-4">Estrutura 2D via API do ChEMBL</p>
            <div className={`grid gap-4 ${
              selected.length === 2 ? 'grid-cols-2' :
              selected.length === 3 ? 'grid-cols-2 lg:grid-cols-3' :
              'grid-cols-2 lg:grid-cols-4'
            }`}>
              {selected.map((c, i) => (
                <MoleculeCard key={c.chembl_id} compound={c} color={COLORS[i]} index={i} />
              ))}
            </div>
          </Section>

          {/* Charts row */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Radar */}
            <Section title="Radar ADMET" delay={0.15}>
              <p className="text-xs text-white/25 mb-2">
                Valores normalizados — mais próximo da borda = melhor druglikeness
              </p>
              {!allAdmetLoaded ? <Loader label="Carregando ADMET..." /> : (
                <AdmetRadar admetData={admetData} compounds={selected} />
              )}
            </Section>

            {/* Scatter */}
            <Section title="ALogP × PSA" delay={0.2}>
              <p className="text-xs text-white/25 mb-2">
                Zona ideal: ALogP &lt; 5 e PSA &lt; 140 Å² (Lipinski + Veber)
              </p>
              {!allAdmetLoaded ? <Loader label="Carregando..." /> : (
                <DruglikenessScatter admetData={admetData} compounds={selected} />
              )}
            </Section>
          </div>

          {/* Comparative table */}
          <Section title="Tabela Comparativa" delay={0.25}>
            <p className="text-xs text-white/25 mb-4">
              <span className="inline-flex items-center gap-1"><CheckCircle size={10} className="text-emerald-400" /> Dentro do range ideal</span>
              <span className="mx-3">·</span>
              <span className="inline-flex items-center gap-1"><XCircle size={10} className="text-red-400" /> Fora do range</span>
            </p>
            {!allAdmetLoaded ? <Loader /> : (
              <CompareTable admetData={admetData} compounds={selected} />
            )}
          </Section>

          {/* Indications chart */}
          <Section title="Indicações por Fase Clínica" delay={0.3}>
            <p className="text-xs text-white/25 mb-2">
              Distribuição das indicações terapêuticas por fase de desenvolvimento
            </p>
            {!allIndicationsLoaded ? <Loader label="Carregando indicações..." /> : (
              <IndicationsChart indicationsData={indicationsData} compounds={selected} />
            )}
          </Section>
        </>
      )}
    </div>
  )
}
