import { Link } from 'react-router-dom'
import { ArrowRight, FlaskConical, Search, Crosshair } from 'lucide-react'
import { useStats } from '../lib/hooks'
import { formatNumber } from '../lib/utils'
import { PageHeader, Section } from '../components/Shell'
import StatCard from '../components/StatCard'
import Loader from '../components/Loader'

export default function HomePage() {
  const { data, isLoading, error } = useStats()

  if (isLoading) return <Loader label="Carregando estatísticas do banco..." />
  if (error) return <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-5 text-red-200">{error.message}</div>

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Overview"
        title="Uma interface simples para explorar o banco"
        description="A API já expõe compostos, ADMET, indicações, mecanismos, bioatividades, artigos e targets. Este frontend organiza tudo isso em uma navegação mais bonita e prática."
        actions={
          <>
            <Link to="/compounds" className="inline-flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-brand-400">
              Explorar compostos <ArrowRight size={16} />
            </Link>
            <Link to="/search" className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/5">
              Busca unificada
            </Link>
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Compostos" value={data.compounds} />
        <StatCard label="Artigos" value={data.articles} helper={`${formatNumber(data.articles_with_abstract)} com abstract`} />
        <StatCard label="Indicações aprovadas" value={data.approved_indications} helper={`${formatNumber(data.indications)} indicações totais`} />
        <StatCard label="Targets" value={data.targets} helper={`QED médio: ${data.avg_qed ?? '—'}`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Section title="Fluxo recomendado do produto" description="A melhor leitura para esse projeto é de explorador científico, não de CRUD administrativo.">
          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                icon: FlaskConical,
                title: 'Compound Explorer',
                description: 'Tabela com filtros de nome, fase clínica, peso molecular, QED e Lipinski.',
              },
              {
                icon: Search,
                title: 'Busca global',
                description: 'Uma barra central para retornar compostos, artigos e targets por relevância.',
              },
              {
                icon: Crosshair,
                title: 'Perfis ricos',
                description: 'Cada composto com overview, ADMET, indicações, mecanismos, bioatividades e artigos relacionados.',
              },
            ].map((item) => (
              <div key={item.title} className="rounded-2xl border border-white/10 bg-slate-900/50 p-5">
                <item.icon className="text-brand-300" size={22} />
                <h3 className="mt-4 text-lg font-medium text-white">{item.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">{item.description}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section title="O que já existe na API" description="Baseado no repositório atual, estes são os blocos centrais que valem virar páginas. ">
          <ul className="space-y-3 text-sm text-slate-300">
            {[
              '/stats para visão geral',
              '/compounds para listagem e filtros',
              '/compounds/{chembl_id} para detalhe',
              '/articles para exploração da literatura',
              '/targets para navegação por alvos biológicos',
              '/search para busca full-text unificada',
            ].map((item) => (
              <li key={item} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">{item}</li>
            ))}
          </ul>
        </Section>
      </div>
    </div>
  )
}
