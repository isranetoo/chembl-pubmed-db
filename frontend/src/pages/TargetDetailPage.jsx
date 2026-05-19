import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from 'recharts'
import {
  ArrowLeft, Crosshair, Dna, FlaskConical, Boxes, Network, ExternalLink,
  Zap, Activity, ArrowUpRight,
} from 'lucide-react'
import { useTarget, useTargetCompounds, useTargetBioactivities } from '../lib/hooks'
import { formatNumber, getPhaseBadgeClass, phaseLabel } from '../lib/utils'
import Section from '../components/Section'
import Loader from '../components/Loader'
import Table from '../components/Table'
import Pill from '../components/Pill'
import Pagination from '../components/Pagination'
import EmptyState from '../components/EmptyState'
import PdbViewer from '../components/PdbViewer'

const PAGE_SIZE = 20

const TOOLTIP_STYLE = {
  backgroundColor: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: 12,
  fontSize: 12,
  fontFamily: 'Kanit',
  color: '#1f2937',
  boxShadow: '0 4px 14px rgba(33,81,83,0.08)',
}

const tabs = [
  { key: 'overview', label: 'Overview', icon: Crosshair },
  { key: 'compounds', label: 'Compostos', icon: FlaskConical },
  { key: 'bioactivities', label: 'Bioatividades', icon: Activity },
  { key: 'annotations', label: 'Anotações', icon: Network },
  { key: 'structures', label: 'Estruturas (PDB)', icon: Boxes },
]

function MetricCard({ label, value, sub }) {
  return (
    <div className="rounded-xl bg-white border border-gray-200 p-4 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5">
      <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1.5">{label}</p>
      <p className="text-lg font-bold text-gray-800">{value}</p>
      {sub && <p className="text-[11px] text-neutral-500 mt-1">{sub}</p>}
    </div>
  )
}

function ExternalLinkBtn({ href, label, mono = false }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-gray-200 bg-white hover:bg-green-50 hover:border-green-300 transition-colors text-[11px] ${mono ? 'font-mono' : ''}`}
    >
      {label}
      <ExternalLink size={10} className="text-gray-400" />
    </a>
  )
}

// ─────────────────────────────────────────────────────────────
// Overview
// ─────────────────────────────────────────────────────────────

function OverviewTab({ target }) {
  const { stats = {}, components = [], pdb_ids = [], xrefs = [] } = target
  const uniprot = components.find((c) => c.accession)?.accession

  const xrefByDb = Object.fromEntries(xrefs.map((x) => [x.src_db, x.ids]))

  return (
    <div className="space-y-5">
      {/* Stats */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Compostos testados" value={formatNumber(stats.distinct_compounds)} sub="únicos" />
        <MetricCard label="Bioatividades" value={formatNumber(stats.total_bioactivities)}
          sub={`${formatNumber(stats.bioactivities_with_pchembl)} com pChEMBL`} />
        <MetricCard label="Potentes (pChEMBL ≥ 7)" value={formatNumber(stats.potent_bioactivities)}
          sub="< 100 nM, drug-like" />
        <MetricCard label="Mediana pChEMBL" value={stats.median_pchembl != null ? stats.median_pchembl.toFixed(2) : '—'}
          sub="potência típica" />
      </div>

      {/* Componentes */}
      <Section title="Componentes proteicos">
        {components.length === 0 ? (
          <p className="text-sm text-neutral-500">Sem componentes anotados.</p>
        ) : (
          <div className="space-y-2">
            {components.map((c, i) => (
              <div key={i} className="rounded-xl bg-gray-50 border border-gray-200 p-4">
                <div className="flex flex-wrap items-center gap-3 mb-2">
                  {c.gene_symbol && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-green-100 border border-green-300 text-xs font-mono font-semibold text-green-800">
                      <Dna size={11} /> {c.gene_symbol}
                    </span>
                  )}
                  {c.accession && (
                    <ExternalLinkBtn
                      href={`https://www.uniprot.org/uniprotkb/${c.accession}`}
                      label={`UniProt ${c.accession}`} mono />
                  )}
                  {c.component_type && (
                    <Pill className="bg-gray-100 text-gray-700 border-gray-200">{c.component_type}</Pill>
                  )}
                  {c.relationship && (
                    <span className="text-[11px] text-neutral-500">{c.relationship}</span>
                  )}
                </div>
                {c.component_description && (
                  <p className="text-xs text-gray-700">{c.component_description}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Quick links */}
      <Section title="Links externos">
        <div className="flex flex-wrap gap-2">
          <ExternalLinkBtn
            href={`https://www.ebi.ac.uk/chembl/target_report_card/${target.chembl_id}/`}
            label={`ChEMBL ${target.chembl_id}`} mono />
          {uniprot && (
            <ExternalLinkBtn href={`https://www.uniprot.org/uniprotkb/${uniprot}`} label={`UniProt ${uniprot}`} mono />
          )}
          {pdb_ids.length > 0 && (
            <ExternalLinkBtn
              href={`https://www.rcsb.org/structure/${pdb_ids[0]}`}
              label={`PDB (${pdb_ids.length})`} />
          )}
          {xrefByDb.Reactome?.[0] && (
            <ExternalLinkBtn
              href={`https://reactome.org/PathwayBrowser/#/${xrefByDb.Reactome[0]}`}
              label={`Reactome (${xrefByDb.Reactome.length})`} />
          )}
          {xrefByDb.HGNC?.[0] && (
            <ExternalLinkBtn
              href={`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${xrefByDb.HGNC[0]}`}
              label="HGNC" />
          )}
        </div>
      </Section>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Compostos
// ─────────────────────────────────────────────────────────────

function CompoundsTab({ chemblId }) {
  const [page, setPage] = useState(1)
  const [minPchembl, setMinPchembl] = useState('')
  const [activityType, setActivityType] = useState('')

  const { data, isLoading, error } = useTargetCompounds(chemblId, {
    page, size: PAGE_SIZE,
    min_pchembl: minPchembl || undefined,
    activity_type: activityType || undefined,
  })

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">pChEMBL mínimo</label>
          <input className="glass-input w-full" type="number" step="0.5" min="0" max="14"
            placeholder="ex: 7"
            value={minPchembl} onChange={(e) => { setMinPchembl(e.target.value); setPage(1) }} />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Tipo de atividade</label>
          <select className="glass-input w-full" value={activityType}
            onChange={(e) => { setActivityType(e.target.value); setPage(1) }}>
            <option value="">Todos</option>
            <option value="IC50">IC50</option>
            <option value="Ki">Ki</option>
            <option value="EC50">EC50</option>
            <option value="Kd">Kd</option>
            <option value="Potency">Potency</option>
          </select>
        </div>
      </div>

      {isLoading ? <Loader label="Carregando compostos..." /> :
       error ? <div className="bg-white border border-rose-300 rounded-xl p-5 text-rose-700 text-sm">{error.message}</div> :
       !data?.items?.length ? <EmptyState /> : (
        <>
          <p className="text-sm text-neutral-500">{formatNumber(data.total)} compostos · página {data.page}/{data.pages}</p>
          <Table columns={[
            {
              key: 'name', header: 'Composto',
              render: (r) => (
                <Link to={`/compounds/${r.chembl_id}`} className="group flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-600 to-green-900 flex items-center justify-center flex-shrink-0">
                    <FlaskConical size={14} className="text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-800 group-hover:text-green-700 transition-colors flex items-center gap-1">
                      {r.name || 'Sem nome'}
                      <ArrowUpRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity text-green-700" />
                    </p>
                    <p className="text-[11px] text-gray-500 font-mono">{r.chembl_id}</p>
                  </div>
                </Link>
              ),
            },
            {
              key: 'best_pchembl', header: 'Melhor pChEMBL',
              render: (r) => r.best_pchembl != null ? (
                <span className={`font-mono text-sm ${r.best_pchembl >= 7 ? 'text-green-700 font-semibold' : 'text-gray-700'}`}>
                  {Number(r.best_pchembl).toFixed(2)}
                </span>
              ) : <span className="text-gray-400">—</span>,
            },
            {
              key: 'best_activity', header: 'Tipo · valor',
              render: (r) => r.best_activity_type ? (
                <div className="text-xs">
                  <span className="font-semibold text-gray-700">{r.best_activity_type}</span>
                  {r.best_value != null && (
                    <span className="text-gray-500 ml-1 font-mono">
                      {Number(r.best_value).toFixed(2)} {r.best_units || ''}
                    </span>
                  )}
                </div>
              ) : '—',
            },
            { key: 'n_bioactivities', header: 'Ensaios', render: (r) => formatNumber(r.n_bioactivities) },
            {
              key: 'phase', header: 'Fase',
              render: (r) => <Pill className={getPhaseBadgeClass(r.max_clinical_phase)}>{phaseLabel(r.max_clinical_phase)}</Pill>,
            },
            {
              key: 'qed', header: 'QED',
              render: (r) => r.qed != null ? (
                <div className="flex items-center gap-2">
                  <div className="w-14 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-to-r from-green-600 to-green-900"
                      style={{ width: `${(Number(r.qed) || 0) * 100}%` }} />
                  </div>
                  <span className="text-xs text-gray-600">{Number(r.qed).toFixed(3)}</span>
                </div>
              ) : <span className="text-gray-400">—</span>,
            },
          ]} rows={data.items} />
          <Pagination page={data.page} pages={data.pages}
            onPrevious={() => setPage((p) => Math.max(1, p - 1))}
            onNext={() => setPage((p) => Math.min(data.pages, p + 1))} />
        </>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Bioatividades (raw)
// ─────────────────────────────────────────────────────────────

function BioactivitiesTab({ chemblId }) {
  const [page, setPage] = useState(1)
  const [activityType, setActivityType] = useState('')
  const [assayType, setAssayType] = useState('')
  const [minPchembl, setMinPchembl] = useState('')

  const { data, isLoading, error } = useTargetBioactivities(chemblId, {
    page, size: PAGE_SIZE,
    activity_type: activityType || undefined,
    assay_type: assayType || undefined,
    min_pchembl: minPchembl || undefined,
  })

  // Mini-chart: distribuição de pChEMBL (top 30 da página atual)
  const pchemblDist = (data?.items ?? [])
    .filter((b) => b.pchembl_value != null)
    .slice(0, 30)
    .map((b, i) => ({
      idx: i + 1,
      pchembl: Number(b.pchembl_value),
      compound: b.compound_name || b.compound_chembl_id,
    }))

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <select className="glass-input" value={activityType}
          onChange={(e) => { setActivityType(e.target.value); setPage(1) }}>
          <option value="">Tipo: todos</option>
          <option value="IC50">IC50</option>
          <option value="Ki">Ki</option>
          <option value="EC50">EC50</option>
          <option value="Kd">Kd</option>
        </select>
        <select className="glass-input" value={assayType}
          onChange={(e) => { setAssayType(e.target.value); setPage(1) }}>
          <option value="">Assay: todos</option>
          <option value="B">B — Binding</option>
          <option value="F">F — Functional</option>
          <option value="A">A — ADME</option>
          <option value="T">T — Toxicity</option>
          <option value="P">P — Physchem</option>
        </select>
        <input className="glass-input" type="number" step="0.5" min="0" max="14"
          placeholder="pChEMBL mínimo (ex: 6)"
          value={minPchembl} onChange={(e) => { setMinPchembl(e.target.value); setPage(1) }} />
      </div>

      {pchemblDist.length > 0 && (
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <p className="text-xs text-neutral-500 mb-2">Distribuição de pChEMBL (top {pchemblDist.length} desta página)</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={pchemblDist}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" />
              <XAxis dataKey="idx" tick={{ fill: '#6b7280', fontSize: 9 }} stroke="rgba(31,41,55,0.1)" />
              <YAxis domain={[0, 'dataMax + 1']} tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" />
              <Tooltip contentStyle={TOOLTIP_STYLE}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const p = payload[0].payload
                  return (
                    <div className="bg-white border border-gray-200 rounded-xl shadow-md p-3 text-xs">
                      <p className="font-semibold text-gray-800 mb-1">{p.compound}</p>
                      <p className="text-gray-700">pChEMBL: <span className="font-mono">{p.pchembl.toFixed(2)}</span></p>
                    </div>
                  )
                }} />
              <Bar dataKey="pchembl" radius={[3, 3, 0, 0]}>
                {pchemblDist.map((d, i) => (
                  <Cell key={i} fill={d.pchembl >= 7 ? '#2f6b14' : '#94a3b8'} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {isLoading ? <Loader label="Carregando bioatividades..." /> :
       error ? <div className="bg-white border border-rose-300 rounded-xl p-5 text-rose-700 text-sm">{error.message}</div> :
       !data?.items?.length ? <EmptyState /> : (
        <>
          <p className="text-sm text-neutral-500">{formatNumber(data.total)} bioatividades · página {data.page}/{data.pages}</p>
          <Table columns={[
            {
              key: 'compound', header: 'Composto',
              render: (r) => (
                <Link to={`/compounds/${r.compound_chembl_id}`} className="text-sm text-gray-800 hover:text-green-700 font-medium">
                  {r.compound_name || r.compound_chembl_id}
                  <span className="block text-[10px] text-gray-500 font-mono">{r.compound_chembl_id}</span>
                </Link>
              ),
            },
            { key: 'activity_type', header: 'Tipo', render: (r) => <span className="text-xs font-semibold text-gray-700">{r.activity_type || '—'}</span> },
            {
              key: 'value', header: 'Valor',
              render: (r) => r.value != null ? (
                <span className="font-mono text-xs">
                  {r.relation && r.relation !== '=' ? `${r.relation} ` : ''}
                  {Number(r.value).toFixed(2)} {r.units || ''}
                </span>
              ) : '—',
            },
            {
              key: 'pchembl', header: 'pChEMBL',
              render: (r) => r.pchembl_value != null ? (
                <span className={`font-mono text-xs ${r.pchembl_value >= 7 ? 'text-green-700 font-semibold' : 'text-gray-700'}`}>
                  {Number(r.pchembl_value).toFixed(2)}
                </span>
              ) : <span className="text-gray-400">—</span>,
            },
            { key: 'assay_type', header: 'Assay', render: (r) => <span className="text-xs text-gray-500">{r.assay_type || '—'}</span> },
            { key: 'year', header: 'Ano', render: (r) => <span className="text-xs text-gray-500">{r.document_year || '—'}</span> },
          ]} rows={data.items} />
          <Pagination page={data.page} pages={data.pages}
            onPrevious={() => setPage((p) => Math.max(1, p - 1))}
            onNext={() => setPage((p) => Math.min(data.pages, p + 1))} />
        </>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Anotações (GO + outros xrefs)
// ─────────────────────────────────────────────────────────────

function AnnotationsTab({ target }) {
  const { go_terms = [], xrefs = [] } = target
  const goByCat = go_terms.reduce((acc, t) => {
    acc[t.category] = acc[t.category] || []
    acc[t.category].push(t)
    return acc
  }, {})

  const catLabels = {
    GoFunction: 'Função molecular',
    GoProcess: 'Processo biológico',
    GoComponent: 'Componente celular',
  }

  return (
    <div className="space-y-5">
      <Section title="Gene Ontology (GO)">
        {Object.keys(goByCat).length === 0 ? (
          <p className="text-sm text-neutral-500">Sem anotações GO.</p>
        ) : (
          <div className="space-y-4">
            {Object.entries(goByCat).map(([cat, items]) => (
              <div key={cat}>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-2">
                  {catLabels[cat] || cat} · {items.length}
                </p>
                <div className="flex flex-wrap gap-2">
                  {items.slice(0, 30).map((t) => (
                    <a key={t.go_id}
                      href={`https://www.ebi.ac.uk/QuickGO/term/${t.go_id}`}
                      target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white border border-gray-200 hover:border-green-300 hover:bg-green-50 transition-colors text-[11px]">
                      <span className="font-mono text-gray-500">{t.go_id}</span>
                      {t.term && <span className="text-gray-700">{t.term}</span>}
                      <ExternalLink size={10} className="text-gray-400" />
                    </a>
                  ))}
                  {items.length > 30 && (
                    <span className="text-[11px] text-neutral-500 self-center">+{items.length - 30} mais…</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Outras referências externas">
        {xrefs.length === 0 ? (
          <p className="text-sm text-neutral-500">Sem cross-references adicionais.</p>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {xrefs.map((g) => (
              <div key={g.src_db} className="rounded-xl bg-gray-50 border border-gray-200 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-600 mb-2">
                  {g.src_db} · {g.ids.length}
                </p>
                <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                  {g.ids.slice(0, 40).map((id) => (
                    <code key={id} className="text-[10px] font-mono text-gray-700 bg-white px-1.5 py-0.5 rounded border border-gray-200">
                      {id}
                    </code>
                  ))}
                  {g.ids.length > 40 && (
                    <span className="text-[10px] text-neutral-500 self-center">+{g.ids.length - 40}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Estruturas PDB
// ─────────────────────────────────────────────────────────────

function StructuresTab({ target }) {
  const { pdb_ids = [] } = target
  const [selected, setSelected] = useState(pdb_ids[0] || null)

  useEffect(() => {
    setSelected(pdb_ids[0] || null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target.chembl_id])

  if (pdb_ids.length === 0) {
    return (
      <div className="rounded-xl bg-white border border-gray-200 p-8 text-center">
        <Boxes size={28} className="mx-auto text-gray-400 mb-2" />
        <p className="text-sm text-neutral-500">Sem estruturas PDB anotadas.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Viewer */}
      {selected && <PdbViewer pdbId={selected} />}

      {/* PDB picker */}
      <Section title={`${pdb_ids.length} estruturas resolvidas`}>
        <p className="text-xs text-neutral-500 mb-3">
          Clique numa estrutura para visualizar. Cartoon + ligantes co-cristalizados são úteis pra
          análise de bolso, docking e estudos de resistência (variantes mutadas).
        </p>
        <div className="grid gap-2 grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 max-h-72 overflow-y-auto pr-1">
          {pdb_ids.map((id) => {
            const isActive = id === selected
            return (
              <button
                key={id}
                onClick={() => setSelected(id)}
                className={`group rounded-lg p-3 text-center transition-all border ${
                  isActive
                    ? 'bg-cyan-50 border-cyan-500 shadow-md'
                    : 'bg-white border-gray-200 hover:border-cyan-300 hover:shadow-sm'
                }`}
              >
                <div className={`w-8 h-8 rounded-md flex items-center justify-center mx-auto mb-2 transition-transform group-hover:scale-110 ${
                  isActive ? 'bg-gradient-to-br from-cyan-600 to-cyan-800' : 'bg-gradient-to-br from-cyan-500 to-cyan-700'
                }`}>
                  <Boxes size={14} className="text-white" />
                </div>
                <p className={`font-mono text-xs font-semibold ${isActive ? 'text-cyan-800' : 'text-gray-800'}`}>
                  {id}
                </p>
                {isActive && (
                  <span className="text-[9px] text-cyan-700 font-semibold uppercase tracking-wider mt-0.5 block">
                    visualizando
                  </span>
                )}
              </button>
            )
          })}
        </div>
        <div className="mt-3 flex items-center gap-2 text-[11px] text-neutral-500">
          <span className="inline-flex items-center gap-1">
            <ExternalLink size={10} /> Viewer powered by 3Dmol.js · dados RCSB PDB
          </span>
        </div>
      </Section>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// MAIN
// ─────────────────────────────────────────────────────────────

export default function TargetDetailPage() {
  const { chemblId } = useParams()
  const [tab, setTab] = useState('overview')

  useEffect(() => { setTab('overview') }, [chemblId])

  const targetQ = useTarget(chemblId)

  if (targetQ.isLoading) return <Loader label="Carregando target..." />
  if (targetQ.error) return (
    <div className="bg-white border border-rose-300 rounded-2xl p-6 text-rose-700 text-sm">
      {targetQ.error.message}
    </div>
  )
  if (!targetQ.data) return null

  const target = targetQ.data
  const uniprot = target.components?.find((c) => c.accession)?.accession
  const genes = (target.components || []).map((c) => c.gene_symbol).filter(Boolean)

  return (
    <div className="space-y-6 pb-8">
      {/* Back */}
      <Link to="/targets" className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-green-700 transition-colors">
        <ArrowLeft size={12} /> Voltar para Targets
      </Link>

      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-2xl shadow-card p-6 animate-fade-in-up">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-violet-700 mb-2">Target</p>
            <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-gray-800 mb-2">
              {target.name}
            </h1>
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <code className="text-xs text-green-800 font-mono bg-green-50 border border-green-200 px-2 py-0.5 rounded">
                {target.chembl_id}
              </code>
              {target.type && <Pill className="bg-gray-100 text-gray-700 border-gray-200">{target.type}</Pill>}
              {target.organism && (
                <span className="text-xs italic text-neutral-500">{target.organism}</span>
              )}
              {target.tax_id && (
                <span className="text-[10px] text-gray-400 font-mono">tax_id:{target.tax_id}</span>
              )}
            </div>
            {genes.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Genes:</span>
                {genes.slice(0, 6).map((g) => (
                  <span key={g} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-green-50 border border-green-200 text-[11px] font-mono font-semibold text-green-800">
                    <Dna size={10} /> {g}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-500 to-violet-700 shadow-md flex-shrink-0">
            <Crosshair size={36} className="text-white" />
          </div>
        </div>

        {/* Quick badges */}
        <div className="grid gap-2 grid-cols-2 lg:grid-cols-4 mt-5">
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Compostos testados</p>
            <p className="text-base font-bold text-gray-800 mt-0.5">{formatNumber(target.stats?.distinct_compounds)}</p>
          </div>
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Potentes (pChEMBL ≥ 7)</p>
            <p className="text-base font-bold text-green-700 mt-0.5 flex items-center gap-1">
              <Zap size={12} /> {formatNumber(target.stats?.potent_bioactivities)}
            </p>
          </div>
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Estruturas PDB</p>
            <p className="text-base font-bold text-cyan-700 mt-0.5 flex items-center gap-1">
              <Boxes size={12} /> {formatNumber(target.pdb_ids?.length)}
            </p>
          </div>
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">UniProt</p>
            <p className="text-base font-bold text-gray-800 mt-0.5 font-mono truncate">
              {uniprot || '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              tab === t.key
                ? 'border-green-700 text-green-800'
                : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'
            }`}
          >
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="animate-fade-in" key={tab}>
        {tab === 'overview' && <OverviewTab target={target} />}
        {tab === 'compounds' && <CompoundsTab chemblId={target.chembl_id} />}
        {tab === 'bioactivities' && <BioactivitiesTab chemblId={target.chembl_id} />}
        {tab === 'annotations' && <AnnotationsTab target={target} />}
        {tab === 'structures' && <StructuresTab target={target} />}
      </div>
    </div>
  )
}
