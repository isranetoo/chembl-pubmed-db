import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useCompound, useCompoundAdmet, useCompoundIndications, useCompoundMechanisms, useCompoundBioactivities, useCompoundArticles } from '../lib/hooks'
import { formatNumber, getPhaseBadgeClass, phaseLabel, getPhaseColor } from '../lib/utils'
import Loader from '../components/Loader'
import Table from '../components/Table'
import Pill from '../components/Pill'
import EmptyState from '../components/EmptyState'
import Section from '../components/Section'
import { ArrowLeft, Atom, Activity, Shield, Zap, BookOpen, FlaskConical, CheckCircle, XCircle, ExternalLink, GitCompareArrows } from 'lucide-react'
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from 'recharts'

const tabs = [
  { key: 'overview', label: 'Overview', icon: Atom },
  { key: 'admet', label: 'ADMET', icon: Activity },
  { key: 'indications', label: 'Indicações', icon: Shield },
  { key: 'mechanisms', label: 'Mecanismos', icon: Zap },
  { key: 'bioactivities', label: 'Bioatividades', icon: FlaskConical },
  { key: 'articles', label: 'Artigos', icon: BookOpen },
]

function MetricCard({ label, value, sub, color = 'white' }) {
  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4 transition-all hover:bg-white/[0.05]">
      <p className="text-[10px] uppercase tracking-wider text-white/30 mb-1.5">{label}</p>
      <p className={`text-lg font-bold ${color === 'emerald' ? 'text-emerald-400' : 'text-white/85'}`} style={{ fontFamily: 'Outfit' }}>{value}</p>
      {sub && <p className="text-[11px] text-white/25 mt-1">{sub}</p>}
    </div>
  )
}

export default function CompoundDetailPage() {
  const { chemblId } = useParams()
  const [tab, setTab] = useState('overview')

  const compoundQ = useCompound(chemblId)
  const admetQ = useCompoundAdmet(chemblId)
  const indicationsQ = useCompoundIndications(chemblId, { size: 50, page: 1 })
  const mechanismsQ = useCompoundMechanisms(chemblId)
  const bioactivitiesQ = useCompoundBioactivities(chemblId, { size: 20, page: 1 })
  const articlesQ = useCompoundArticles(chemblId, { size: 10, page: 1, only_abstract: true })

  if (compoundQ.isLoading) return <Loader label="Carregando composto..." />
  if (compoundQ.error) return <div className="glass-card p-5 border-red-500/20 text-red-300 text-sm">{compoundQ.error.message}</div>

  const c = compoundQ.data
  const admet = admetQ.data
  const indications = indicationsQ.data
  const mechanisms = mechanismsQ.data
  const bioactivities = bioactivitiesQ.data
  const articles = articlesQ.data

  return (
    <div className="space-y-6 pb-8">
      {/* Back + Header */}
      <div className="animate-fade-in-up">
        <Link to="/compounds" className="inline-flex items-center gap-1.5 text-sm text-white/40 hover:text-white/70 transition-colors mb-4">
          <ArrowLeft size={14} /> Voltar
        </Link>
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-400/60 mb-1 font-mono">{c.chembl_id}</p>
            <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit' }}>
              {c.name || 'Composto'}
            </h1>
          </div>
          {c.smiles && (
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] px-4 py-2 max-w-md">
              <p className="text-[10px] text-white/30 mb-0.5">SMILES</p>
              <code className="text-[11px] text-emerald-300/50 break-all font-mono">{c.smiles}</code>
            </div>
          )}
        </div>
      </div>

      {/* Identity cards */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4 animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
        <MetricCard label="Fórmula" value={c.molecular_formula || '—'} />
        <MetricCard label="Peso molecular" value={formatNumber(c.mol_weight, { maximumFractionDigits: 2 })} />
        <MetricCard label="InChI Key" value={c.inchi_key ? `${c.inchi_key.slice(0, 14)}...` : '—'} sub={c.inchi_key} />
        <MetricCard label="QED" value={admet ? formatNumber(admet.qed_weighted, { maximumFractionDigits: 4 }) : '—'} color="emerald" />
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5 p-1.5 rounded-xl bg-white/[0.03] border border-white/[0.06] animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
              tab === t.key
                ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/20 shadow-sm'
                : 'text-white/40 hover:text-white/70 hover:bg-white/[0.04] border border-transparent'
            }`}>
            <t.icon size={15} />
            <span className="hidden sm:inline">{t.label}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="space-y-4 animate-fade-in">
          {/* Top row: molecule + radar */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Molecular structure */}
            <Section title="Estrutura Molecular">
              <div className="flex flex-col items-center">
                <div className="w-full max-w-[280px] aspect-square rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-center overflow-hidden mb-3">
                  <img
                    src={`https://www.ebi.ac.uk/chembl/api/data/image/${c.chembl_id}.svg`}
                    alt={`Estrutura 2D de ${c.name}`}
                    className="w-full h-full object-contain p-4 invert opacity-80"
                    onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
                  />
                  <div className="hidden flex-col items-center gap-2 text-white/20">
                    <Atom size={36} />
                    <span className="text-xs">Imagem indisponível</span>
                  </div>
                </div>
                {c.smiles && (
                  <code className="text-[10px] text-emerald-300/40 font-mono text-center break-all px-4 max-w-sm">{c.smiles}</code>
                )}
                <Link to={`/compare?add=${c.chembl_id}`}
                  className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium text-white/40 border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] hover:text-white/70 transition-all">
                  <GitCompareArrows size={13} /> Comparar com outro
                </Link>
              </div>
            </Section>

            {/* ADMET Radar */}
            <Section title="Radar ADMET">
              {admetQ.isLoading ? <Loader /> : admet ? (() => {
                const norm = (val, max) => val != null ? Math.min(Math.max(val / max, 0), 1) : 0
                const radarData = [
                  { prop: 'QED', value: norm(admet.qed_weighted, 1) },
                  { prop: 'Lipofilia', value: Math.max(0, 1 - norm(Math.abs(admet.alogp || 0), 7)) },
                  { prop: 'Polaridade', value: Math.max(0, 1 - norm(admet.psa || 0, 200)) },
                  { prop: 'HBD', value: Math.max(0, 1 - norm(admet.hbd || 0, 7)) },
                  { prop: 'HBA', value: Math.max(0, 1 - norm(admet.hba || 0, 15)) },
                  { prop: 'Flexibilidade', value: Math.max(0, 1 - norm(admet.rtb || 0, 15)) },
                ]
                return (
                  <>
                    <ResponsiveContainer width="100%" height={280}>
                      <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="72%">
                        <PolarGrid stroke="rgba(255,255,255,0.06)" />
                        <PolarAngleAxis dataKey="prop" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'Outfit' }} />
                        <PolarRadiusAxis angle={30} domain={[0, 1]} tick={false} axisLine={false} />
                        <Radar dataKey="value" stroke="#34d399" fill="#34d399" fillOpacity={0.15} strokeWidth={2} dot={{ r: 3, fill: '#34d399' }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 12 }}
                          formatter={(v) => [(v * 100).toFixed(0) + '%']}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                    <p className="text-[10px] text-white/20 text-center mt-1">Mais próximo da borda = melhor druglikeness</p>
                  </>
                )
              })() : <EmptyState description="Sem dados ADMET." />}
            </Section>
          </div>

          {/* ADMET metrics + Lipinski/PAINS badges */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Section title="Propriedades ADMET">
              {admetQ.isLoading ? <Loader /> : admet ? (
                <div className="grid grid-cols-2 gap-3">
                  <MetricCard label="QED" value={formatNumber(admet.qed_weighted, { maximumFractionDigits: 4 })} color="emerald" />
                  <MetricCard label="ALogP" value={formatNumber(admet.alogp, { maximumFractionDigits: 3 })} />
                  <MetricCard label="PSA (Å²)" value={formatNumber(admet.psa, { maximumFractionDigits: 2 })} />
                  <MetricCard label="HBD / HBA" value={`${admet.hbd ?? '—'} / ${admet.hba ?? '—'}`} />
                  <MetricCard label="Rotatable Bonds" value={admet.rtb ?? '—'} />
                  <MetricCard label="Ro5 violações" value={admet.num_ro5_violations ?? '—'} />
                  <div className="col-span-2 flex gap-3">
                    <div className={`flex-1 rounded-xl p-3 flex items-center gap-2 ${admet.lipinski_pass ? 'bg-emerald-500/10 border border-emerald-500/15' : 'bg-red-500/10 border border-red-500/15'}`}>
                      {admet.lipinski_pass ? <CheckCircle size={16} className="text-emerald-400" /> : <XCircle size={16} className="text-red-400" />}
                      <span className="text-xs font-medium text-white/60">Lipinski</span>
                    </div>
                    <div className={`flex-1 rounded-xl p-3 flex items-center gap-2 ${admet.veber_pass ? 'bg-emerald-500/10 border border-emerald-500/15' : 'bg-amber-500/10 border border-amber-500/15'}`}>
                      {admet.veber_pass ? <CheckCircle size={16} className="text-emerald-400" /> : <XCircle size={16} className="text-amber-400" />}
                      <span className="text-xs font-medium text-white/60">Veber</span>
                    </div>
                    <div className={`flex-1 rounded-xl p-3 flex items-center gap-2 ${admet.pains_free ? 'bg-emerald-500/10 border border-emerald-500/15' : 'bg-amber-500/10 border border-amber-500/15'}`}>
                      {admet.pains_free ? <CheckCircle size={16} className="text-emerald-400" /> : <XCircle size={16} className="text-amber-400" />}
                      <span className="text-xs font-medium text-white/60">PAINS</span>
                    </div>
                  </div>
                </div>
              ) : <EmptyState description="Sem dados ADMET." />}
            </Section>

            {/* Indications phase chart */}
            <Section title="Indicações por Fase">
              {indicationsQ.isLoading ? <Loader /> : indications?.items?.length > 0 ? (() => {
                const phaseCounts = {}
                indications.items.forEach((ind) => {
                  const lbl = phaseLabel(ind.max_phase)
                  phaseCounts[lbl] = (phaseCounts[lbl] || 0) + 1
                })
                const phaseData = Object.entries(phaseCounts)
                  .map(([name, count]) => ({ name, count }))
                  .sort((a, b) => {
                    const order = ['Approved', 'Phase 3', 'Phase 2', 'Phase 1', 'Early Phase 1', 'Preclinical', '—']
                    return order.indexOf(a.name) - order.indexOf(b.name)
                  })
                const phaseBarColors = {
                  'Approved': '#10b981', 'Phase 3': '#3b82f6', 'Phase 2': '#f59e0b',
                  'Phase 1': '#f97316', 'Early Phase 1': '#6b7280', 'Preclinical': '#475569', '—': '#334155'
                }
                return (
                  <>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={phaseData} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                        <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} stroke="rgba(255,255,255,0.06)" allowDecimals={false} />
                        <YAxis type="category" dataKey="name" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11, fontFamily: 'Outfit' }} stroke="rgba(255,255,255,0.06)" width={90} />
                        <Tooltip contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 12 }} />
                        <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={24}>
                          {phaseData.map((entry) => (
                            <Cell key={entry.name} fill={phaseBarColors[entry.name] || '#475569'} fillOpacity={0.7} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-xs text-white/25 text-center">{formatNumber(indications.total)} indicações totais</p>
                  </>
                )
              })() : <EmptyState description="Sem indicações registradas." />}
            </Section>
          </div>

          {/* Quick stats */}
          <div className="grid grid-cols-3 gap-3">
            <MetricCard label="Indicações" value={formatNumber(indications?.total || 0)} />
            <MetricCard label="Mecanismos" value={formatNumber(mechanisms?.total || 0)} />
            <MetricCard label="Artigos" value={formatNumber(articles?.total || 0)} />
          </div>
        </div>
      )}

      {tab === 'admet' && (
        <Section title="ADMET completo" delay={0}>
          {admetQ.isLoading ? <Loader /> : admet ? (
            <Table columns={[
              { key: 'prop', header: 'Propriedade' },
              { key: 'val', header: 'Valor' },
            ]} rows={[
              { prop: 'ALogP', val: admet.alogp }, { prop: 'CX LogP', val: admet.cx_logp },
              { prop: 'CX LogD', val: admet.cx_logd }, { prop: 'PSA', val: admet.psa },
              { prop: 'QED', val: admet.qed_weighted }, { prop: 'HBD', val: admet.hbd },
              { prop: 'HBA', val: admet.hba }, { prop: 'Ro5 violations', val: admet.num_ro5_violations },
              { prop: 'Heavy atoms', val: admet.heavy_atoms }, { prop: 'Aromatic rings', val: admet.aromatic_rings },
              { prop: 'RTB', val: admet.rtb }, { prop: 'Molecular species', val: admet.molecular_species },
              { prop: 'Lipinski pass', val: admet.lipinski_pass ? '✓ Yes' : '✗ No' },
              { prop: 'Veber pass', val: admet.veber_pass ? '✓ Yes' : '✗ No' },
              { prop: 'PAINS free', val: admet.pains_free ? '✓ Yes' : '✗ No' },
            ]} />
          ) : <EmptyState description="Sem dados ADMET." />}
        </Section>
      )}

      {tab === 'indications' && (
        <Section title="Indicações terapêuticas" delay={0}>
          {indicationsQ.isLoading ? <Loader /> : (
            <Table columns={[
              { key: 'mesh_heading', header: 'Indicação', render: (r) => r.mesh_heading || r.efo_term || '—' },
              { key: 'efo_term', header: 'EFO' },
              { key: 'max_phase', header: 'Fase', render: (r) => <Pill className={getPhaseBadgeClass(r.max_phase)}>{phaseLabel(r.max_phase)}</Pill> },
            ]} rows={indications?.items || []} emptyMessage="Nenhuma indicação." />
          )}
        </Section>
      )}

      {tab === 'mechanisms' && (
        <Section title="Mecanismos de ação" delay={0}>
          {mechanismsQ.isLoading ? <Loader /> : !mechanisms?.items?.length ? <EmptyState description="Nenhum mecanismo." /> : (
            <div className="space-y-3">
              {mechanisms.items.map((m) => (
                <div key={m.mec_id} className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-5 transition-all hover:bg-white/[0.05]">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-white/85">{m.mechanism_of_action || m.action_type || 'Mecanismo'}</h3>
                      <p className="text-xs text-white/35 mt-1">{m.target_name || '—'}</p>
                    </div>
                    {m.action_type && <Pill className="bg-violet-500/15 text-violet-300 border-violet-500/20">{m.action_type}</Pill>}
                  </div>
                  {m.mechanism_comment && <p className="mt-3 text-xs text-white/30 leading-relaxed">{m.mechanism_comment}</p>}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {tab === 'bioactivities' && (
        <Section title="Bioatividades" delay={0}>
          {bioactivitiesQ.isLoading ? <Loader /> : (
            <Table columns={[
              { key: 'target_name', header: 'Target' },
              { key: 'organism', header: 'Organismo' },
              { key: 'activity_type', header: 'Tipo' },
              { key: 'value', header: 'Valor', render: (r) => formatNumber(r.value, { maximumFractionDigits: 2 }) },
              { key: 'units', header: 'Unidade' },
              { key: 'relation', header: 'Rel.' },
            ]} rows={bioactivities?.items || []} emptyMessage="Nenhuma bioatividade." />
          )}
        </Section>
      )}

      {tab === 'articles' && (
        <Section title="Artigos relacionados" delay={0}>
          {articlesQ.isLoading ? <Loader /> : !articles?.items?.length ? <EmptyState description="Nenhum artigo." /> : (
            <div className="space-y-3">
              {articles.items.map((a) => (
                <div key={a.pmid} className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-5 transition-all hover:bg-white/[0.05]">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-white/85 leading-snug">{a.title}</h3>
                      <p className="text-xs text-white/30 mt-1.5">{a.journal || '—'} · {a.pub_year || '—'} · PMID {a.pmid}</p>
                    </div>
                    <a href={`https://pubmed.ncbi.nlm.nih.gov/${a.pmid}/`} target="_blank" rel="noreferrer"
                      className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-white/50 hover:text-white/80 hover:bg-white/[0.06] transition-all flex-shrink-0">
                      PubMed <ExternalLink size={11} />
                    </a>
                  </div>
                  {a.abstract && <p className="mt-3 text-xs text-white/30 leading-relaxed line-clamp-3">{a.abstract.slice(0, 350)}...</p>}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}
    </div>
  )
}
