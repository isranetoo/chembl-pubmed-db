import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useCompound, useCompoundAdmet, useCompoundIndications, useCompoundMechanisms, useCompoundBioactivities, useCompoundArticles } from '../lib/hooks'
import { formatNumber, getPhaseBadgeClass, phaseLabel, getPhaseColor } from '../lib/utils'
import Loader from '../components/Loader'
import Table from '../components/Table'
import Pill from '../components/Pill'
import EmptyState from '../components/EmptyState'
import Section from '../components/Section'
import { ArrowLeft, Atom, Activity, Shield, Zap, BookOpen, FlaskConical, CheckCircle, XCircle, ExternalLink } from 'lucide-react'

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
        <div className="grid gap-4 lg:grid-cols-2 animate-fade-in">
          <Section title="Resumo ADMET">
            {admetQ.isLoading ? <Loader /> : admet ? (
              <div className="grid grid-cols-2 gap-3">
                <MetricCard label="ALogP" value={formatNumber(admet.alogp, { maximumFractionDigits: 3 })} />
                <MetricCard label="PSA (Å²)" value={formatNumber(admet.psa, { maximumFractionDigits: 2 })} />
                <MetricCard label="HBD / HBA" value={`${admet.hbd ?? '—'} / ${admet.hba ?? '—'}`} />
                <MetricCard label="Ro5 violações" value={admet.num_ro5_violations ?? '—'} />
                <div className="col-span-2 flex gap-3">
                  <div className={`flex-1 rounded-xl p-3 flex items-center gap-2 ${admet.lipinski_pass ? 'bg-emerald-500/10 border border-emerald-500/15' : 'bg-red-500/10 border border-red-500/15'}`}>
                    {admet.lipinski_pass ? <CheckCircle size={16} className="text-emerald-400" /> : <XCircle size={16} className="text-red-400" />}
                    <span className="text-xs font-medium text-white/60">Lipinski</span>
                  </div>
                  <div className={`flex-1 rounded-xl p-3 flex items-center gap-2 ${admet.pains_free ? 'bg-emerald-500/10 border border-emerald-500/15' : 'bg-amber-500/10 border border-amber-500/15'}`}>
                    {admet.pains_free ? <CheckCircle size={16} className="text-emerald-400" /> : <XCircle size={16} className="text-amber-400" />}
                    <span className="text-xs font-medium text-white/60">PAINS</span>
                  </div>
                </div>
              </div>
            ) : <EmptyState description="Sem dados ADMET." />}
          </Section>

          <Section title="Resumo clínico">
            <div className="space-y-4">
              {indications?.items?.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {indications.items.slice(0, 8).map((ind) => (
                    <Pill key={ind.drugind_id} className={getPhaseBadgeClass(ind.max_phase)}>
                      {ind.mesh_heading || ind.efo_term || phaseLabel(ind.max_phase)}
                    </Pill>
                  ))}
                </div>
              )}
              <div className="grid grid-cols-3 gap-3">
                <MetricCard label="Indicações" value={formatNumber(indications?.total || 0)} />
                <MetricCard label="Mecanismos" value={formatNumber(mechanisms?.total || 0)} />
                <MetricCard label="Artigos" value={formatNumber(articles?.total || 0)} />
              </div>
            </div>
          </Section>
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
