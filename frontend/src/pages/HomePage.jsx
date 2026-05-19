import { Link } from 'react-router-dom'
import {
  ArrowRight, FlaskConical, Search, Crosshair, Activity,
  Shield, BookOpen, Pill as PillIcon, AlertTriangle, Ban,
  Award, Microscope, TestTube2, FileText, Dna, Boxes, Stethoscope, Zap,
} from 'lucide-react'
import { useStats } from '../lib/hooks'
import { formatNumber } from '../lib/utils'
import StatCard from '../components/StatCard'
import Loader from '../components/Loader'
import Section from '../components/Section'

// Mini stat used inside thematic sections — compact format.
function MiniStat({ label, value, helper, icon: Icon, accent = 'text-gray-800' }) {
  return (
    <div className="rounded-xl bg-white border border-gray-200 p-4 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1.5">{label}</p>
          <p className={`text-xl font-bold ${accent}`}>
            {formatNumber(value)}
          </p>
          {helper && <p className="mt-1 text-[10px] text-neutral-500">{helper}</p>}
        </div>
        {Icon && <Icon size={14} className="text-gray-400 flex-shrink-0 mt-1" />}
      </div>
    </div>
  )
}

export default function HomePage() {
  const { data, isLoading, error } = useStats()

  if (isLoading) return <Loader label="Carregando estatísticas do banco..." />
  if (error) return (
    <div className="bg-white border border-rose-300 rounded-2xl p-6 animate-fade-in">
      <p className="text-rose-700 text-sm">{error.message}</p>
    </div>
  )

  return (
    <div className="space-y-6 pb-8">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl bg-white border border-gray-200 shadow-card p-8 lg:p-10 animate-fade-in-up">
        <div className="absolute -top-20 -right-20 w-64 h-64 bg-green-200/30 rounded-full blur-[80px]" />
        <div className="absolute -bottom-10 -left-10 w-48 h-48 bg-green-100/40 rounded-full blur-[60px]" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-50 border border-green-200 mb-4">
              <span className="w-1.5 h-1.5 rounded-full bg-green-600" style={{ animation: 'pulse-dot 2s ease-in-out infinite' }} />
              <span className="text-[11px] font-semibold text-green-800 uppercase tracking-wider">Banco ativo</span>
            </div>
            <h1 className="text-3xl lg:text-5xl font-bold tracking-tight mb-3 text-gray-800">
              Explore compostos,
              <br />
              <span className="bg-gradient-to-br from-green-600 to-green-900 text-transparent bg-clip-text">
                descubra evidências.
              </span>
            </h1>
            <p className="text-sm lg:text-base text-neutral-600 leading-relaxed max-w-md">
              Navegue por dados farmacológicos do ChEMBL, ensaios clínicos da CT.gov e literatura do PubMed em uma interface unificada.
            </p>
          </div>

          <div className="hidden lg:flex relative items-center justify-center w-44 h-44 flex-shrink-0">
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-green-200/60 to-green-100/40 blur-2xl" />
            <div className="relative w-40 h-40 rounded-3xl flex items-center justify-center shadow-elevated">
              <img src="/assets/img/logo.png" alt="DrugXpert" className="w-28 h-28 object-contain drop-shadow-lg" />
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/compounds"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium text-white bg-gradient-to-br from-green-600 to-green-900 shadow-md transition-all duration-300 hover:shadow-xl hover:scale-[1.03]"
            >
              Explorar compostos <ArrowRight size={16} />
            </Link>
            <Link
              to="/search"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium text-gray-800 border border-[#215153] bg-white transition-all duration-300 hover:bg-gray-50 hover:scale-[1.03]"
            >
              <Search size={16} /> Buscar
            </Link>
          </div>
        </div>
      </div>

      {/* Top-level stats grid */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Compostos" value={data.compounds} icon={FlaskConical} color="emerald" delay={0.05}
          helper={`${formatNumber(data.approved_drugs)} aprovados · ${formatNumber(data.compounds_with_admet)} com ADMET`} />
        <StatCard label="Artigos" value={data.articles} icon={BookOpen} color="sky" delay={0.1}
          helper={`${formatNumber(data.articles_with_abstract)} com abstract · até ${data.latest_article_year ?? '—'}`} />
        <StatCard label="Indicações aprovadas" value={data.approved_indications} icon={Shield} color="amber" delay={0.15}
          helper={`${formatNumber(data.indications)} total`} />
        <StatCard label="Ensaios clínicos" value={data.total_trials} icon={Stethoscope} color="rose" delay={0.2}
          helper={`${formatNumber(data.compounds_with_trials)} compostos cobertos`} />
      </div>

      {/* Drug pipeline */}
      <Section title="Drug pipeline & segurança" delay={0.25}>
        <p className="text-[11px] text-neutral-500 mb-3 -mt-1">
          Status regulatório dos compostos do banco — dados de fase clínica, vias de administração, warnings FDA e drogas retiradas.
        </p>
        <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
          <MiniStat label="Aprovados (FDA)" value={data.approved_drugs} icon={Award}
            accent="text-green-700" helper="max_phase = 4" />
          <MiniStat label="Em Fase 3" value={data.phase3_drugs} icon={TestTube2}
            accent="text-sky-700" helper="Última fase pré-aprovação" />
          <MiniStat label="Black box" value={data.black_box_drugs} icon={AlertTriangle}
            accent="text-amber-700" helper="Warning FDA grave" />
          <MiniStat label="Withdrawn" value={data.withdrawn_drugs} icon={Ban}
            accent="text-rose-700" helper="Retiradas do mercado" />
          <MiniStat label="Via oral" value={data.oral_drugs} icon={PillIcon}
            accent="text-blue-700" />
          <MiniStat label="Parenteral" value={data.parenteral_drugs} icon={PillIcon}
            accent="text-violet-700" />
          <MiniStat label="First-in-class" value={data.first_in_class_drugs} icon={Award}
            accent="text-green-700" helper="Mecanismo inovador" />
          <MiniStat label="Drogas órfãs" value={data.orphan_drugs} icon={Shield}
            accent="text-fuchsia-700" helper="Doenças raras" />
        </div>
        <div className="grid gap-3 grid-cols-2 lg:grid-cols-3 mt-3">
          <MiniStat label="Tipos moleculares" value={data.distinct_molecule_types} icon={Boxes}
            helper="Small mol, antibody, …" />
          <MiniStat label="Sinônimos (INN/BAN/trade)" value={data.total_synonyms} icon={FileText} />
          <MiniStat label="Códigos ATC" value={data.total_atc_codes} icon={FileText}
            helper="Classificação WHO" />
        </div>
      </Section>

      {/* Bioactivity */}
      <Section title="Bioatividade — qualidade dos dados" delay={0.3}>
        <p className="text-[11px] text-neutral-500 mb-3 -mt-1">
          Métricas padronizadas pra ranking de potência: pChEMBL ≥ 7 corresponde a IC₅₀ &lt; 100 nM (drug-like).
          Ensaios em variantes mutadas (T315I etc) são essenciais pra estudar resistência.
        </p>
        <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
          <MiniStat label="Total bioatividades" value={data.bioactivities} icon={Activity} />
          <MiniStat label="Com pChEMBL" value={data.bioactivities_with_pchembl} icon={TestTube2}
            accent="text-sky-700"
            helper={data.bioactivities ? `${Math.round(100*(data.bioactivities_with_pchembl/data.bioactivities))}% padronizadas` : ''} />
          <MiniStat label="Potentes (pChEMBL ≥ 7)" value={data.potent_bioactivities} icon={Zap}
            accent="text-green-700" helper="< 100 nM, drug-like" />
          <MiniStat label="Em mutações" value={data.bioactivities_with_mutation} icon={Dna}
            accent="text-amber-700" helper="Estudos de resistência" />
          <MiniStat label="Tipos de assay" value={data.distinct_assay_types} icon={Microscope}
            helper="B / F / A / T / P" />
          <MiniStat label="Jornais distintos" value={data.distinct_journals} icon={BookOpen}
            helper="Fontes literárias" />
          <MiniStat label="Mecanismos" value={data.mechanisms} icon={Zap} />
          <MiniStat label="Com variante anotada" value={data.mechanisms_with_variant} icon={Dna}
            accent="text-amber-700" helper="variant_sequence" />
        </div>
      </Section>

      {/* Targets */}
      <Section title="Alvos biológicos enriquecidos" delay={0.35}>
        <p className="text-[11px] text-neutral-500 mb-3 -mt-1">
          Cada alvo conecta-se a UniProt (proteína), gene oficial (HGNC), estruturas 3D do PDB e anotações funcionais GO/Reactome.
        </p>
        <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
          <MiniStat label="Total targets" value={data.targets} icon={Crosshair} />
          <MiniStat label="Enriquecidos" value={data.enriched_targets} icon={Crosshair}
            accent="text-violet-700"
            helper={data.targets ? `${Math.round(100*(data.enriched_targets/data.targets))}% com tax_id + UniProt` : ''} />
          <MiniStat label="Genes únicos" value={data.distinct_genes} icon={Dna}
            accent="text-green-700" helper="HGNC gene symbols" />
          <MiniStat label="Estruturas PDB" value={data.total_pdb_structures} icon={Boxes}
            accent="text-cyan-700" helper="Cristal/Cryo-EM" />
        </div>
      </Section>

      {/* Features grid (Website-style: white card with top green border) */}
      <div className="grid gap-4 lg:grid-cols-3">
        {[
          {
            icon: FlaskConical,
            title: 'Compound Explorer',
            desc: 'Filtre por fase clínica, QED, peso molecular, Lipinski e muito mais.',
            link: '/compounds',
          },
          {
            icon: Search,
            title: 'Busca Full-Text',
            desc: 'Encontre compostos, artigos e targets usando busca unificada por relevância.',
            link: '/search',
          },
          {
            icon: Activity,
            title: 'Perfis Completos',
            desc: 'ADMET, indicações, mecanismos, bioatividades, trials e literatura em uma tela.',
            link: '/compounds',
          },
        ].map((item, i) => (
          <Link
            to={item.link}
            key={item.title}
            className="group bg-white rounded-xl shadow-md hover:shadow-lg transition-all duration-300 border-t-4 border-[#5c8d2f] border-x border-b border-gray-200 p-6 animate-fade-in-up cursor-pointer hover:-translate-y-1"
            style={{ animationDelay: `${(i + 3) * 0.08}s` }}
          >
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-green-600 to-green-900 flex items-center justify-center shadow-md mb-4 transition-transform duration-300 group-hover:scale-110">
              <item.icon size={20} className="text-white" />
            </div>
            <h3 className="text-base font-semibold text-gray-800 mb-2">{item.title}</h3>
            <p className="text-sm text-neutral-500 leading-relaxed">{item.desc}</p>
            <div className="mt-4 flex items-center gap-1 text-xs font-medium text-green-700 group-hover:text-green-900 transition-colors">
              Acessar <ArrowRight size={12} className="transition-transform group-hover:translate-x-1" />
            </div>
          </Link>
        ))}
      </div>

      {/* Endpoints / banco geral */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Banco — qualidade & cobertura" delay={0.45}>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'QED médio', value: data.avg_qed, helper: 'Drug-likeness 0–1' },
              { label: 'Compostos com ADMET', value: data.compounds_with_admet },
              { label: 'Artigo mais recente', value: data.latest_article_year },
              { label: 'Compostos com trials', value: data.compounds_with_trials },
            ].map((s) => (
              <div key={s.label} className="rounded-xl bg-gray-50 border border-gray-200 p-4">
                <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">{s.label}</p>
                <p className="text-xl font-bold text-gray-800">{formatNumber(s.value)}</p>
                {s.helper && <p className="text-[10px] text-neutral-500 mt-1">{s.helper}</p>}
              </div>
            ))}
          </div>
        </Section>

        <Section title="Endpoints da API" delay={0.5}>
          <div className="space-y-2">
            {[
              '/compounds — listagem + filtros (fase, QED, MW, Lipinski)',
              '/compounds/{id} — detalhe + metadata clínico/ATC',
              '/compounds/{id}/bioactivities — com pChEMBL, assay, gene, jornal',
              '/compounds/{id}/mechanisms — com gene + variant_sequence',
              '/compounds/{id}/trials — ClinicalTrials.gov sincronizado',
              '/search — full-text unificada',
              '/stats — métricas do banco (este dashboard)',
            ].map((ep) => (
              <div key={ep} className="flex items-center gap-3 rounded-lg bg-gray-50 border border-gray-200 px-3 py-2.5 text-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-green-600 flex-shrink-0" />
                <code className="text-gray-700 font-mono">{ep}</code>
              </div>
            ))}
          </div>
        </Section>
      </div>
    </div>
  )
}
