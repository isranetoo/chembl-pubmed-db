import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Microscope, Activity, FlaskConical, ChevronDown, ChevronUp, BarChart3, Info } from "lucide-react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/* ── Fetch helpers ─────────────────────────────────────────────────────────── */

const fetchHistopathology = async (chemblId) => {
  const res = await fetch(`${API}/compounds/${chemblId}/histopathology`);
  if (!res.ok) throw new Error("Erro ao buscar dados de histopatologia");
  return res.json();
};

const fetchCohortTme = async (cohort) => {
  const res = await fetch(`${API}/histopathology/cohorts/${cohort}/tme`);
  if (!res.ok) throw new Error("Erro ao buscar TME");
  return res.json();
};

/* ── Utilidades ────────────────────────────────────────────────────────────── */

const CELL_TYPES = [
  { key: "cancer_cell",  label: "Células Tumorais", color: "#E74C3C" },
  { key: "lymphocytes",  label: "Linfócitos (TILs)", color: "#3498DB" },
  { key: "fibroblasts",  label: "Fibroblastos",     color: "#2ECC71" },
  { key: "neutrophils",  label: "Neutrófilos",       color: "#F39C12" },
  { key: "plasmocytes",  label: "Plasmócitos",       color: "#9B59B6" },
  { key: "eosinophils",  label: "Eosinófilos",       color: "#1ABC9C" },
];

const formatNumber = (n) => {
  if (n == null) return "—";
  if (Math.abs(n) < 0.001) return n.toExponential(2);
  if (Math.abs(n) > 10000) return n.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  return n.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
};

/* ── Barra horizontal simples ──────────────────────────────────────────────── */

function HorizontalBar({ value, maxValue, color, label, sublabel }) {
  const pct = maxValue > 0 ? Math.min((value / maxValue) * 100, 100) : 0;

  return (
    <div className="mb-3">
      <div className="flex justify-between items-baseline mb-1">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-xs text-gray-500">{sublabel}</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out flex items-center justify-end pr-2"
          style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: color }}
        >
          {pct > 15 && (
            <span className="text-[10px] font-bold text-white">
              {formatNumber(value)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Card de coorte ────────────────────────────────────────────────────────── */

function CohortCard({ cohort }) {
  const [expanded, setExpanded] = useState(false);

  const { data: tmeData, isLoading } = useQuery({
    queryKey: ["cohort-tme", cohort.tcga_cohort],
    queryFn: () => fetchCohortTme(cohort.tcga_cohort),
    enabled: expanded,
    staleTime: 5 * 60 * 1000,
  });

  // Extrair densidades globais pra gráfico de composição celular
  const getDensity = (cellKey) => {
    if (!tmeData?.stats) return 0;
    const feat = tmeData.stats.find(
      (s) => s.feature === `global_density_${cellKey}`
    );
    return feat?.mean || 0;
  };

  const densities = CELL_TYPES.map((ct) => ({
    ...ct,
    value: getDensity(ct.key),
  }));
  const maxDensity = Math.max(...densities.map((d) => d.value), 0.001);

  // TILs diffusivity
  const tilsDiff = tmeData?.stats?.find(
    (s) => s.feature === "tils_diffusivity"
  );

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <button
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center">
            <Microscope className="w-5 h-5 text-rose-600" />
          </div>
          <div className="text-left">
            <p className="font-semibold text-gray-900">
              {cohort.cancer_name}
            </p>
            <p className="text-xs text-gray-500">
              {cohort.tcga_cohort} · via indicação: {cohort.indication}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {cohort.tme_features_cached > 0 && (
            <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
              {cohort.tme_features_cached} features
            </span>
          )}
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 border-t border-gray-100">
          {isLoading ? (
            <div className="py-8 text-center text-sm text-gray-500">
              Carregando dados do microambiente tumoral...
            </div>
          ) : !tmeData?.stats?.length ? (
            <div className="py-8 text-center">
              <Info className="w-8 h-8 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">
                Dados TME ainda não cacheados para esta coorte.
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Execute o populate do Owkin para buscar estatísticas.
              </p>
            </div>
          ) : (
            <div className="mt-4 space-y-6">
              {/* TILs Diffusivity highlight */}
              {tilsDiff && (
                <div className="bg-blue-50 rounded-lg p-4 flex items-start gap-3">
                  <Activity className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-blue-900">
                      TILs Diffusivity
                    </p>
                    <p className="text-2xl font-bold text-blue-700 mt-1">
                      {formatNumber(tilsDiff.mean)}
                    </p>
                    <p className="text-xs text-blue-600 mt-1">
                      Mede quão espalhados estão os linfócitos infiltrantes de
                      tumor. Valores altos sugerem maior resposta imune
                      antitumoral.
                    </p>
                  </div>
                </div>
              )}

              {/* Composição celular */}
              <div>
                <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  Composição Celular (densidade global média)
                </h4>
                {densities.map((d) => (
                  <HorizontalBar
                    key={d.key}
                    value={d.value}
                    maxValue={maxDensity}
                    color={d.color}
                    label={d.label}
                    sublabel={`média: ${formatNumber(d.value)}`}
                  />
                ))}
              </div>

              {/* Tabela de features detalhada */}
              <details className="group">
                <summary className="cursor-pointer text-sm font-medium text-gray-600 hover:text-gray-900 flex items-center gap-1">
                  <FlaskConical className="w-4 h-4" />
                  Ver todas as features ({tmeData.stats.length})
                </summary>
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2 pr-3 text-gray-500 font-medium">Feature</th>
                        <th className="text-right py-2 px-2 text-gray-500 font-medium">Média</th>
                        <th className="text-right py-2 px-2 text-gray-500 font-medium">Std</th>
                        <th className="text-right py-2 px-2 text-gray-500 font-medium">Min</th>
                        <th className="text-right py-2 px-2 text-gray-500 font-medium">P50</th>
                        <th className="text-right py-2 px-2 text-gray-500 font-medium">Max</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tmeData.stats.map((s) => (
                        <tr key={s.feature} className="border-b border-gray-50 hover:bg-gray-50">
                          <td className="py-1.5 pr-3 text-gray-700 font-mono truncate max-w-[200px]">
                            {s.feature}
                          </td>
                          <td className="text-right py-1.5 px-2 text-gray-900 font-medium">
                            {formatNumber(s.mean)}
                          </td>
                          <td className="text-right py-1.5 px-2 text-gray-500">
                            {formatNumber(s.std)}
                          </td>
                          <td className="text-right py-1.5 px-2 text-gray-500">
                            {formatNumber(s.min)}
                          </td>
                          <td className="text-right py-1.5 px-2 text-gray-500">
                            {formatNumber(s.p50)}
                          </td>
                          <td className="text-right py-1.5 px-2 text-gray-500">
                            {formatNumber(s.max)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Componente principal: HistopathologyTab ────────────────────────────────── */

export default function HistopathologyTab({ chemblId }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["histopathology", chemblId],
    queryFn: () => fetchHistopathology(chemblId),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="py-12 text-center text-sm text-gray-500">
        <Microscope className="w-8 h-8 text-gray-300 mx-auto mb-3 animate-pulse" />
        Buscando dados histopatológicos...
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center text-sm text-red-500">
        Erro ao carregar dados de histopatologia: {error.message}
      </div>
    );
  }

  if (!data?.cohorts?.length) {
    return (
      <div className="py-12 text-center">
        <Microscope className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-600 font-medium">
          Sem dados histopatológicos disponíveis
        </p>
        <p className="text-sm text-gray-400 mt-2 max-w-md mx-auto">
          Este composto não possui indicações oncológicas mapeadas a coortes
          TCGA. Apenas compostos com indicações em câncer têm dados do Owkin
          Pathology Explorer.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Microscope className="w-5 h-5 text-rose-600" />
            Histopatologia (TCGA)
          </h3>
          <p className="text-sm text-gray-500 mt-0.5">
            Microambiente tumoral via Owkin Pathology Explorer ·{" "}
            {data.total_cohorts} coorte{data.total_cohorts > 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Info banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-xs text-amber-800">
        <strong>Fonte:</strong> Dados de detecção celular por IA (Owkin) em
        lâminas H&E do TCGA. O modelo detecta 13 tipos celulares para análise
        quantitativa do microambiente tumoral. Coortes mapeadas automaticamente
        via indicações do composto.
      </div>

      {/* Cohort cards */}
      <div className="space-y-3">
        {data.cohorts.map((cohort) => (
          <CohortCard key={cohort.tcga_cohort} cohort={cohort} />
        ))}
      </div>
    </div>
  );
}
