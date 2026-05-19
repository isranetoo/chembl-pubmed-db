import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useCompound, useCompoundAdmet, useCompoundIndications, useCompoundMechanisms, useCompoundBioactivities, useCompoundArticles } from '../lib/hooks'
import { formatNumber, getPhaseBadgeClass, phaseLabel } from '../lib/utils'
import Loader from '../components/Loader'
import Table from '../components/Table'
import Pill from '../components/Pill'
import EmptyState from '../components/EmptyState'
import Section from '../components/Section'
import Pagination from '../components/Pagination'
import ClinicalTrialsTab from '../components/ClinicalTrialsTab'

const PAGE_SIZE = 10
import { ArrowLeft, Atom, Activity, Shield, Zap, BookOpen, FlaskConical, CheckCircle, XCircle, ExternalLink, GitCompareArrows, Stethoscope, AlertTriangle, Ban, Pill as PillIcon, Tag } from 'lucide-react'
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
  { key: 'trials', label: 'Clinical Status', icon: Stethoscope },
  { key: 'articles', label: 'Artigos', icon: BookOpen },
]

function MetricCard({ label, value, sub, color = 'gray' }) {
  return (
    <div className="rounded-xl bg-white border border-gray-200 p-4 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5">
      <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1.5">{label}</p>
      <p className={`text-lg font-bold ${color === 'emerald' ? 'text-green-700' : 'text-gray-800'}`}>{value}</p>
      {sub && <p className="text-[11px] text-neutral-500 mt-1">{sub}</p>}
    </div>
  )
}

export default function CompoundDetailPage() {
  const { chemblId } = useParams()
  const [tab, setTab] = useState('overview')
  const [indicationsPage, setIndicationsPage] = useState(1)
  const [bioactivitiesPage, setBioactivitiesPage] = useState(1)
  const [articlesPage, setArticlesPage] = useState(1)

  // Trocar de composto reseta paginação de todas as abas.
  useEffect(() => {
    setIndicationsPage(1)
    setBioactivitiesPage(1)
    setArticlesPage(1)
  }, [chemblId])

  const compoundQ = useCompound(chemblId)
  const admetQ = useCompoundAdmet(chemblId)
  // Set "full" pro chart do Overview (cap do backend é 200).
  // O queryKey muda quando params muda → cache separado da query paginada.
  const indicationsAllQ = useCompoundIndications(chemblId, { size: 200, page: 1 })
  const indicationsQ = useCompoundIndications(chemblId, { size: PAGE_SIZE, page: indicationsPage })
  const mechanismsQ = useCompoundMechanisms(chemblId)
  const bioactivitiesQ = useCompoundBioactivities(chemblId, { size: PAGE_SIZE, page: bioactivitiesPage })
  const articlesQ = useCompoundArticles(chemblId, { size: PAGE_SIZE, page: articlesPage, only_abstract: true })

  if (compoundQ.isLoading) return <Loader label="Carregando composto..." />
  if (compoundQ.error) return <div className="bg-white border border-rose-300 rounded-xl p-5 text-rose-700 text-sm">{compoundQ.error.message}</div>

  const c = compoundQ.data
  const admet = admetQ.data
  const indicationsAll = indicationsAllQ.data
  const indications = indicationsQ.data
  const mechanisms = mechanismsQ.data
  const bioactivities = bioactivitiesQ.data
  const articles = articlesQ.data

  return (
    <div className="space-y-6 pb-8">
      {/* Back + Header */}
      <div className="animate-fade-in-up">
        <Link to="/compounds" className="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-green-700 transition-colors mb-4">
          <ArrowLeft size={14} /> Voltar
        </Link>
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-green-700 mb-1 font-mono">{c.chembl_id}</p>
            <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-gray-800">
              {c.name || 'Composto'}
            </h1>

            {/* Clinical / regulatory badges */}
            <div className="flex flex-wrap items-center gap-1.5 mt-3">
              {c.max_phase !== null && c.max_phase !== undefined && (
                <Pill className={getPhaseBadgeClass(c.max_phase)}>
                  {phaseLabel(c.max_phase)}
                  {c.first_approval ? ` · ${c.first_approval}` : ''}
                </Pill>
              )}
              {c.molecule_type && (
                <Pill className="bg-gray-100 text-gray-700 border-gray-300">{c.molecule_type}</Pill>
              )}
              {c.oral && (
                <Pill className="bg-blue-100 text-blue-800 border-blue-300">
                  <PillIcon size={11} className="inline mr-1" />Oral
                </Pill>
              )}
              {c.parenteral && (
                <Pill className="bg-violet-100 text-violet-800 border-violet-300">Parenteral</Pill>
              )}
              {c.topical && (
                <Pill className="bg-teal-100 text-teal-800 border-teal-300">Topical</Pill>
              )}
              {c.first_in_class && (
                <Pill className="bg-green-100 text-green-800 border-green-300">First-in-class</Pill>
              )}
              {c.prodrug && (
                <Pill className="bg-gray-100 text-gray-700 border-gray-300">Prodrug</Pill>
              )}
              {c.orphan && (
                <Pill className="bg-fuchsia-100 text-fuchsia-800 border-fuchsia-300">Orphan</Pill>
              )}
              {c.natural_product && (
                <Pill className="bg-lime-100 text-lime-800 border-lime-300">Natural product</Pill>
              )}
              {c.black_box_warning && (
                <Pill className="bg-amber-100 text-amber-800 border-amber-300">
                  <AlertTriangle size={11} className="inline mr-1" />Black box warning
                </Pill>
              )}
              {c.withdrawn_flag && (
                <Pill className="bg-rose-100 text-rose-800 border-rose-300" title={c.withdrawn_reason || ''}>
                  <Ban size={11} className="inline mr-1" />
                  Withdrawn{c.withdrawn_year ? ` · ${c.withdrawn_year}` : ''}
                </Pill>
              )}
              {c.atc?.[0]?.level5 && (
                <Pill className="bg-gray-100 text-gray-700 border-gray-300 font-mono" title={c.atc[0].level1_description || ''}>
                  <Tag size={11} className="inline mr-1" />ATC {c.atc[0].level5}
                </Pill>
              )}
            </div>

            {/* Drug class (USAN stem) */}
            {c.usan_stem_definition && (
              <p className="text-xs text-neutral-600 mt-2">
                Classe farmacológica: <span className="text-gray-800 font-medium">{c.usan_stem_definition}</span>
                {c.usan_stem && <span className="text-gray-500 font-mono"> ({c.usan_stem})</span>}
              </p>
            )}

            {/* Trade names / synonyms */}
            {c.synonyms?.length > 0 && (() => {
              const trade = c.synonyms
                .filter((s) => ['TRADE_NAME', 'OTHER', 'BRAND_NAME', 'MERCK_INDEX'].includes(s.syn_type))
                .map((s) => s.synonym)
                .filter((v, i, arr) => arr.indexOf(v) === i)
                .slice(0, 6)
              if (trade.length === 0) return null
              return (
                <p className="text-xs text-neutral-600 mt-1">
                  Também conhecido como: <span className="text-gray-800">{trade.join(', ')}</span>
                </p>
              )
            })()}
          </div>

          {c.smiles && (
            <div className="rounded-xl bg-gray-50 border border-gray-200 px-4 py-2 max-w-md flex-shrink-0">
              <p className="text-[10px] text-gray-500 font-semibold mb-0.5">SMILES</p>
              <code className="text-[11px] text-green-800 break-all font-mono">{c.smiles}</code>
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
      <div className="flex flex-wrap gap-1.5 p-1.5 rounded-xl bg-gray-50 border border-gray-200 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
              tab === t.key
                ? 'bg-gradient-to-br from-green-600 to-green-900 text-white shadow-md'
                : 'text-gray-600 hover:text-green-700 hover:bg-white border border-transparent'
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
                <div className="w-full max-w-[280px] aspect-square rounded-xl bg-gray-50 border border-gray-200 flex items-center justify-center overflow-hidden mb-3">
                  <img
                    src={`https://www.ebi.ac.uk/chembl/api/data/image/${c.chembl_id}.svg`}
                    alt={`Estrutura 2D de ${c.name}`}
                    className="w-full h-full object-contain p-4"
                    onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
                  />
                  <div className="hidden flex-col items-center gap-2 text-gray-400">
                    <Atom size={36} />
                    <span className="text-xs">Imagem indisponível</span>
                  </div>
                </div>
                {c.smiles && (
                  <code className="text-[10px] text-green-800 font-mono text-center break-all px-4 max-w-sm">{c.smiles}</code>
                )}
                <Link to={`/compare?add=${c.chembl_id}`}
                  className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium text-gray-700 border border-gray-200 bg-white hover:border-[#5c8d2f] hover:text-green-800 hover:bg-green-50 transition-all">
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
                        <PolarGrid stroke="rgba(31,41,55,0.08)" />
                        <PolarAngleAxis dataKey="prop" tick={{ fill: '#4b5563', fontSize: 11, fontFamily: 'Kanit' }} />
                        <PolarRadiusAxis angle={30} domain={[0, 1]} tick={false} axisLine={false} />
                        <Radar dataKey="value" stroke="#2f6b14" fill="#5c8d2f" fillOpacity={0.25} strokeWidth={2} dot={{ r: 3, fill: '#2f6b14' }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, fontSize: 12, color: '#1f2937' }}
                          formatter={(v) => [(v * 100).toFixed(0) + '%']}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                    <p className="text-[10px] text-gray-500 text-center mt-1">Mais próximo da borda = melhor druglikeness</p>
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
                    <div className={`flex-1 rounded-xl p-3 flex items-center gap-2 ${admet.lipinski_pass ? 'bg-green-50 border border-green-200' : 'bg-rose-50 border border-rose-200'}`}>
                      {admet.lipinski_pass ? <CheckCircle size={16} className="text-green-700" /> : <XCircle size={16} className="text-rose-600" />}
                      <span className="text-xs font-semibold text-gray-700">Lipinski</span>
                    </div>
                    <div className={`flex-1 rounded-xl p-3 flex items-center gap-2 ${admet.veber_pass ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
                      {admet.veber_pass ? <CheckCircle size={16} className="text-green-700" /> : <XCircle size={16} className="text-amber-600" />}
                      <span className="text-xs font-semibold text-gray-700">Veber</span>
                    </div>
                    <div className={`flex-1 rounded-xl p-3 flex items-center gap-2 ${admet.pains_free ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
                      {admet.pains_free ? <CheckCircle size={16} className="text-green-700" /> : <XCircle size={16} className="text-amber-600" />}
                      <span className="text-xs font-semibold text-gray-700">PAINS</span>
                    </div>
                  </div>
                </div>
              ) : <EmptyState description="Sem dados ADMET." />}
            </Section>

            {/* Indications phase chart */}
            <Section title="Indicações por Fase">
              {indicationsAllQ.isLoading ? <Loader /> : indicationsAll?.items?.length > 0 ? (() => {
                const phaseCounts = {}
                indicationsAll.items.forEach((ind) => {
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
                  'Approved': '#2f6b14', 'Phase 3': '#0369a1', 'Phase 2': '#d97706',
                  'Phase 1': '#ea580c', 'Early Phase 1': '#6b7280', 'Preclinical': '#4b5563', '—': '#9ca3af'
                }
                return (
                  <>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={phaseData} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.06)" horizontal={false} />
                        <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} stroke="rgba(31,41,55,0.1)" allowDecimals={false} />
                        <YAxis type="category" dataKey="name" tick={{ fill: '#4b5563', fontSize: 11, fontFamily: 'Kanit' }} stroke="rgba(31,41,55,0.1)" width={90} />
                        <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, fontSize: 12, color: '#1f2937' }} />
                        <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={24}>
                          {phaseData.map((entry) => (
                            <Cell key={entry.name} fill={phaseBarColors[entry.name] || '#9ca3af'} fillOpacity={0.85} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-xs text-gray-500 text-center">{formatNumber(indicationsAll.total)} indicações totais</p>
                  </>
                )
              })() : <EmptyState description="Sem indicações registradas." />}
            </Section>
          </div>

          {/* Quick stats */}
          <div className="grid grid-cols-3 gap-3">
            <MetricCard label="Indicações" value={formatNumber(indicationsAll?.total || 0)} />
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
            <div className="space-y-3">
              <Table columns={[
                { key: 'mesh_heading', header: 'Indicação', render: (r) => r.mesh_heading || r.efo_term || '—' },
                { key: 'efo_term', header: 'EFO' },
                { key: 'max_phase', header: 'Fase', render: (r) => <Pill className={getPhaseBadgeClass(r.max_phase)}>{phaseLabel(r.max_phase)}</Pill> },
              ]} rows={indications?.items || []} emptyMessage="Nenhuma indicação." />
              <Pagination
                page={indicationsPage}
                pages={indications?.pages || 0}
                onPrevious={() => setIndicationsPage((p) => Math.max(1, p - 1))}
                onNext={() => setIndicationsPage((p) => Math.min(indications?.pages || 1, p + 1))}
              />
            </div>
          )}
        </Section>
      )}

      {tab === 'mechanisms' && (
        <Section title="Mecanismos de ação" delay={0}>
          {mechanismsQ.isLoading ? <Loader /> : !mechanisms?.items?.length ? <EmptyState description="Nenhum mecanismo." /> : (
            <div className="space-y-3">
              {mechanisms.items.map((m) => (
                <div key={m.mec_id} className="rounded-xl bg-white border border-gray-200 p-5 shadow-sm transition-all hover:shadow-md hover:border-[#5c8d2f]">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-gray-800">{m.mechanism_of_action || m.action_type || 'Mecanismo'}</h3>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <p className="text-xs text-neutral-500">{m.target_name || '—'}</p>
                        {m.gene_symbol && (
                          <span className="text-[10px] font-mono text-green-800 bg-green-50 border border-green-200 rounded px-1.5 py-0.5">
                            {m.gene_symbol}
                          </span>
                        )}
                        {m.uniprot_accession && (
                          <a
                            href={`https://www.uniprot.org/uniprotkb/${m.uniprot_accession}/entry`}
                            target="_blank" rel="noreferrer"
                            className="text-[10px] font-mono text-gray-500 hover:text-green-700 transition-colors"
                            title="UniProt"
                          >
                            {m.uniprot_accession} ↗
                          </a>
                        )}
                        {m.variant_sequence?.mutation && (
                          <span className="text-[10px] text-amber-800 font-mono bg-amber-50 border border-amber-300 rounded px-1.5 py-0.5"
                                title={m.variant_sequence?.organism || ''}>
                            mut: {m.variant_sequence.mutation}
                          </span>
                        )}
                      </div>
                    </div>
                    {m.action_type && <Pill className="bg-violet-100 text-violet-800 border-violet-300">{m.action_type}</Pill>}
                  </div>
                  {m.mechanism_comment && <p className="mt-3 text-xs text-neutral-600 leading-relaxed">{m.mechanism_comment}</p>}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {tab === 'bioactivities' && (
        <Section title="Bioatividades" delay={0}>
          {bioactivitiesQ.isLoading ? <Loader /> : (
            <div className="space-y-3">
              <p className="text-[11px] text-neutral-500">
                <span className="font-semibold text-gray-700">pChEMBL</span> = −log₁₀(IC50/Ki em molar) — quanto maior, mais potente.
                <span className="ml-2 text-green-700">≥ 8 alta</span>
                <span className="ml-2 text-sky-700">7–8 boa</span>
                <span className="ml-2 text-amber-700">6–7 moderada</span>
                <span className="ml-2 text-gray-500">&lt; 6 fraca</span>
              </p>
              <Table columns={[
                {
                  key: 'target_name',
                  header: 'Target',
                  render: (r) => (
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="text-gray-800 font-medium truncate">{r.target_name || '—'}</span>
                        {r.gene_symbol && (
                          <span className="text-[10px] font-mono text-green-800 bg-green-50 border border-green-200 rounded px-1 flex-shrink-0">
                            {r.gene_symbol}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        {r.uniprot_accession && (
                          <a
                            href={`https://www.uniprot.org/uniprotkb/${r.uniprot_accession}/entry`}
                            target="_blank" rel="noreferrer"
                            className="text-[10px] font-mono text-gray-500 hover:text-green-700 transition-colors"
                            title="UniProt"
                          >
                            {r.uniprot_accession} ↗
                          </a>
                        )}
                        {r.assay_variant_mutation && (
                          <span className="text-[10px] text-amber-700 font-mono">mut: {r.assay_variant_mutation}</span>
                        )}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'organism',
                  header: 'Organismo',
                  render: (r) => <span className="text-gray-600 text-xs italic">{r.organism || '—'}</span>,
                },
                {
                  key: 'activity_type',
                  header: 'Tipo',
                  render: (r) => (
                    <div className="flex items-center gap-1.5">
                      <span className="text-gray-800">{r.activity_type || '—'}</span>
                      {r.assay_type && (
                        <Pill className="bg-gray-100 text-gray-600 border-gray-200 !px-1.5 !py-0 !text-[10px]" title={
                          { B: 'Binding', F: 'Functional', A: 'ADME', T: 'Toxicity', P: 'Physchem' }[r.assay_type] || r.assay_type
                        }>{r.assay_type}</Pill>
                      )}
                    </div>
                  ),
                },
                {
                  key: 'value',
                  header: 'Valor',
                  render: (r) => {
                    const v = r.standard_value ?? r.value
                    const u = r.standard_units || r.units
                    return (
                      <span className="font-mono text-xs text-gray-800">
                        {r.relation && r.relation !== '=' ? r.relation + ' ' : ''}
                        {formatNumber(v, { maximumFractionDigits: 3 })} {u || ''}
                      </span>
                    )
                  },
                },
                {
                  key: 'pchembl_value',
                  header: 'pChEMBL',
                  render: (r) => {
                    if (r.pchembl_value == null) return <span className="text-gray-400">—</span>
                    const p = Number(r.pchembl_value)
                    const cls = p >= 8 ? 'bg-green-100 text-green-800 border-green-300'
                              : p >= 7 ? 'bg-sky-100 text-sky-800 border-sky-300'
                              : p >= 6 ? 'bg-amber-100 text-amber-800 border-amber-300'
                                       : 'bg-gray-100 text-gray-700 border-gray-300'
                    return <Pill className={`${cls} font-mono`}>{p.toFixed(2)}</Pill>
                  },
                },
                {
                  key: 'document',
                  header: 'Fonte',
                  render: (r) => r.document_year || r.document_journal ? (
                    <div className="text-[11px] text-neutral-500 truncate max-w-[160px]" title={r.document_journal || ''}>
                      {r.document_journal || '—'}
                      {r.document_year && <span className="text-gray-400 ml-1">· {r.document_year}</span>}
                    </div>
                  ) : <span className="text-gray-400">—</span>,
                },
                {
                  key: 'le',
                  header: 'LE',
                  render: (r) => r.le != null ? (
                    <span className="font-mono text-[11px] text-gray-700" title={`BEI=${r.bei ?? '—'} | LLE=${r.lle ?? '—'} | SEI=${r.sei ?? '—'}`}>
                      {Number(r.le).toFixed(2)}
                    </span>
                  ) : <span className="text-gray-400">—</span>,
                },
              ]} rows={bioactivities?.items || []} emptyMessage="Nenhuma bioatividade." />
              <Pagination
                page={bioactivitiesPage}
                pages={bioactivities?.pages || 0}
                onPrevious={() => setBioactivitiesPage((p) => Math.max(1, p - 1))}
                onNext={() => setBioactivitiesPage((p) => Math.min(bioactivities?.pages || 1, p + 1))}
              />
            </div>
          )}
        </Section>
      )}

      {tab === 'trials' && (
        <Section title="Clinical Status" delay={0}>
          <ClinicalTrialsTab chemblId={c.chembl_id} drugName={c.name} />
        </Section>
      )}

      {tab === 'articles' && (
        <Section title="Artigos relacionados" delay={0}>
          {articlesQ.isLoading ? <Loader /> : !articles?.items?.length ? <EmptyState description="Nenhum artigo." /> : (
            <div className="space-y-3">
              {articles.items.map((a) => (
                <div key={a.pmid} className="rounded-xl bg-white border border-gray-200 p-5 shadow-sm transition-all hover:shadow-md hover:border-[#5c8d2f]">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-gray-800 leading-snug">{a.title}</h3>
                      <p className="text-xs text-neutral-500 mt-1.5">{a.journal || '—'} · {a.pub_year || '—'} · PMID {a.pmid}</p>
                    </div>
                    <a href={`https://pubmed.ncbi.nlm.nih.gov/${a.pmid}/`} target="_blank" rel="noreferrer"
                      className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 hover:text-green-700 hover:border-[#5c8d2f] hover:bg-green-50 transition-all flex-shrink-0">
                      PubMed <ExternalLink size={11} />
                    </a>
                  </div>
                  {a.abstract && <p className="mt-3 text-xs text-neutral-600 leading-relaxed line-clamp-3">{a.abstract.slice(0, 350)}...</p>}
                </div>
              ))}
              <Pagination
                page={articlesPage}
                pages={articles?.pages || 0}
                onPrevious={() => setArticlesPage((p) => Math.max(1, p - 1))}
                onNext={() => setArticlesPage((p) => Math.min(articles?.pages || 1, p + 1))}
              />
            </div>
          )}
        </Section>
      )}
    </div>
  )
}
