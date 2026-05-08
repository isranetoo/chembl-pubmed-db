import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useCompound, useCompoundAdmet, useCompoundIndications, useCompoundMechanisms, useCompoundBioactivities, useCompoundArticles } from '../lib/hooks'
import { formatNumber, getPhaseBadgeClass, phaseLabel } from '../lib/utils'
import { PageHeader, Section } from '../components/Shell'
import Loader from '../components/Loader'
import Table from '../components/Table'
import Pill from '../components/Pill'
import EmptyState from '../components/EmptyState'

const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'admet', label: 'ADMET' },
  { key: 'indications', label: 'Indications' },
  { key: 'mechanisms', label: 'Mechanisms' },
  { key: 'bioactivities', label: 'Bioactivities' },
  { key: 'articles', label: 'Articles' },
]

export default function CompoundDetailPage() {
  const { chemblId } = useParams()
  const [tab, setTab] = useState('overview')

  const compoundQuery = useCompound(chemblId)
  const admetQuery = useCompoundAdmet(chemblId)
  const indicationsQuery = useCompoundIndications(chemblId, { size: 20, page: 1 })
  const mechanismsQuery = useCompoundMechanisms(chemblId)
  const bioactivitiesQuery = useCompoundBioactivities(chemblId, { size: 20, page: 1 })
  const articlesQuery = useCompoundArticles(chemblId, { size: 10, page: 1, only_abstract: true })

  if (compoundQuery.isLoading) return <Loader label="Carregando perfil do composto..." />
  if (compoundQuery.error) return <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5 text-red-200">{compoundQuery.error.message}</div>

  const compound = compoundQuery.data
  const admet = admetQuery.data
  const indications = indicationsQuery.data
  const mechanisms = mechanismsQuery.data
  const bioactivities = bioactivitiesQuery.data
  const articles = articlesQuery.data

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={compound.chembl_id}
        title={compound.name || 'Composto sem nome'}
        description="A página do composto deve concentrar tudo o que interessa sobre essa entidade, em vez de espalhar contexto em telas diferentes."
      />

      <Section>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Metric label="Fórmula" value={compound.molecular_formula} />
          <Metric label="Peso molecular" value={formatNumber(compound.mol_weight, { maximumFractionDigits: 2 })} />
          <Metric label="InChI Key" value={compound.inchi_key || '—'} />
          <Metric label="SMILES" value={compound.smiles || '—'} />
        </div>
      </Section>

      <div className="flex flex-wrap gap-2">
        {tabs.map((item) => (
          <button
            key={item.key}
            onClick={() => setTab(item.key)}
            className={[
              'rounded-xl border px-4 py-2 text-sm transition',
              tab === item.key
                ? 'border-brand-400/30 bg-brand-500/15 text-brand-200'
                : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10',
            ].join(' ')}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Section title="Resumo ADMET">
            {admetQuery.isLoading ? <Loader label="Carregando ADMET..." /> : admet ? (
              <div className="grid gap-3 md:grid-cols-2">
                <Metric label="QED" value={formatNumber(admet.qed_weighted, { maximumFractionDigits: 4 })} />
                <Metric label="ALogP" value={formatNumber(admet.alogp, { maximumFractionDigits: 3 })} />
                <Metric label="PSA" value={formatNumber(admet.psa, { maximumFractionDigits: 2 })} />
                <Metric label="HBD / HBA" value={`${admet.hbd ?? '—'} / ${admet.hba ?? '—'}`} />
                <Metric label="Lipinski" value={admet.lipinski_pass ? 'Pass' : 'Fail'} />
                <Metric label="PAINS" value={admet.pains_free ? 'Free' : 'Alertas detectados'} />
              </div>
            ) : <EmptyState description="Esse composto não tem dados ADMET disponíveis." />}
          </Section>

          <Section title="Resumo clínico">
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {(indications?.items || []).slice(0, 6).map((item) => (
                  <Pill key={item.drugind_id} className={getPhaseBadgeClass(item.max_phase)}>
                    {phaseLabel(item.max_phase)}
                  </Pill>
                ))}
              </div>
              <p className="text-sm text-slate-400">
                {formatNumber(indications?.total || 0)} indicações, {formatNumber(mechanisms?.total || 0)} mecanismos e {formatNumber(articles?.total || 0)} artigos associados.
              </p>
            </div>
          </Section>
        </div>
      )}

      {tab === 'admet' && (
        <Section title="ADMET detalhado">
          {admetQuery.isLoading ? <Loader label="Carregando ADMET..." /> : admet ? (
            <Table
              columns={[
                { key: 'property', header: 'Propriedade' },
                { key: 'value', header: 'Valor' },
              ]}
              rows={[
                { property: 'ALogP', value: admet.alogp },
                { property: 'CX LogP', value: admet.cx_logp },
                { property: 'CX LogD', value: admet.cx_logd },
                { property: 'PSA', value: admet.psa },
                { property: 'QED', value: admet.qed_weighted },
                { property: 'HBD', value: admet.hbd },
                { property: 'HBA', value: admet.hba },
                { property: 'Ro5 violations', value: admet.num_ro5_violations },
                { property: 'Heavy atoms', value: admet.heavy_atoms },
                { property: 'Aromatic rings', value: admet.aromatic_rings },
                { property: 'PAINS free', value: admet.pains_free ? 'Yes' : 'No' },
              ]}
            />
          ) : <EmptyState description="Esse composto não tem dados ADMET disponíveis." />}
        </Section>
      )}

      {tab === 'indications' && (
        <Section title="Indicações terapêuticas">
          {indicationsQuery.isLoading ? <Loader label="Carregando indicações..." /> : (
            <Table
              columns={[
                { key: 'mesh_heading', header: 'Mesh heading', render: (row) => row.mesh_heading || row.efo_term || '—' },
                { key: 'efo_term', header: 'EFO term' },
                {
                  key: 'max_phase',
                  header: 'Fase',
                  render: (row) => <Pill className={getPhaseBadgeClass(row.max_phase)}>{phaseLabel(row.max_phase)}</Pill>,
                },
              ]}
              rows={indications?.items || []}
              emptyMessage="Nenhuma indicação encontrada."
            />
          )}
        </Section>
      )}

      {tab === 'mechanisms' && (
        <Section title="Mecanismos de ação">
          {mechanismsQuery.isLoading ? <Loader label="Carregando mecanismos..." /> : !mechanisms?.items?.length ? <EmptyState description="Nenhum mecanismo encontrado." /> : (
            <div className="space-y-4">
              {mechanisms.items.map((item) => (
                <div key={item.mec_id} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h3 className="text-base font-medium text-white">{item.mechanism_of_action || item.action_type || 'Mechanism'}</h3>
                      <p className="mt-1 text-sm text-slate-400">{item.target_name || 'Target não informado'}</p>
                    </div>
                    {item.action_type ? <Pill className="border-white/10 bg-white/5 text-slate-200">{item.action_type}</Pill> : null}
                  </div>
                  {item.mechanism_comment ? <p className="mt-4 text-sm leading-6 text-slate-300">{item.mechanism_comment}</p> : null}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {tab === 'bioactivities' && (
        <Section title="Bioatividades">
          {bioactivitiesQuery.isLoading ? <Loader label="Carregando bioatividades..." /> : (
            <Table
              columns={[
                { key: 'target_name', header: 'Target' },
                { key: 'organism', header: 'Organism' },
                { key: 'activity_type', header: 'Tipo' },
                { key: 'value', header: 'Valor' },
                { key: 'units', header: 'Unidade' },
                { key: 'relation', header: 'Relação' },
              ]}
              rows={bioactivities?.items || []}
              emptyMessage="Nenhuma bioatividade encontrada."
            />
          )}
        </Section>
      )}

      {tab === 'articles' && (
        <Section title="Artigos relacionados">
          {articlesQuery.isLoading ? <Loader label="Carregando artigos..." /> : !articles?.items?.length ? <EmptyState description="Nenhum artigo relacionado foi encontrado." /> : (
            <div className="space-y-4">
              {articles.items.map((article) => (
                <article key={article.pmid} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h3 className="text-base font-medium text-white">{article.title}</h3>
                      <p className="mt-1 text-sm text-slate-400">{article.journal || 'Journal não informado'} • {article.pub_year || 'Ano não informado'}</p>
                    </div>
                    <a
                      href={`https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/`}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-xl border border-white/10 px-3 py-2 text-sm text-white hover:bg-white/5"
                    >
                      Ver no PubMed
                    </a>
                  </div>
                  {article.abstract ? <p className="mt-4 text-sm leading-6 text-slate-300">{article.abstract.slice(0, 420)}...</p> : null}
                </article>
              ))}
            </div>
          )}
        </Section>
      )}
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 break-words text-sm font-medium text-white">{value}</p>
    </div>
  )
}
