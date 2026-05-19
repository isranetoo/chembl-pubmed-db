import { useMemo, useState } from 'react'
import {
  Wrench, FlaskConical, Zap, Calculator, ShieldCheck, ShieldAlert,
  ArrowRightLeft, Atom, Beaker, Sigma, Scale,
} from 'lucide-react'
import Section from '../components/Section'
import Pill from '../components/Pill'

// ─────────────────────────────────────────────────────────────
// Tool 1 — Lipinski / Veber rule checker
// ─────────────────────────────────────────────────────────────

function LipinskiChecker() {
  const [vals, setVals] = useState({ mw: '', alogp: '', hbd: '', hba: '', psa: '', rtb: '' })

  const num = (k) => (vals[k] === '' ? null : Number(vals[k]))
  const mw = num('mw'), alogp = num('alogp'), hbd = num('hbd'), hba = num('hba'), psa = num('psa'), rtb = num('rtb')

  const checks = [
    { label: 'MW ≤ 500 Da', pass: mw == null ? null : mw <= 500, value: mw, rule: 'Lipinski' },
    { label: 'ALogP ≤ 5', pass: alogp == null ? null : alogp <= 5, value: alogp, rule: 'Lipinski' },
    { label: 'HBD ≤ 5', pass: hbd == null ? null : hbd <= 5, value: hbd, rule: 'Lipinski' },
    { label: 'HBA ≤ 10', pass: hba == null ? null : hba <= 10, value: hba, rule: 'Lipinski' },
    { label: 'PSA ≤ 140 Å²', pass: psa == null ? null : psa <= 140, value: psa, rule: 'Veber' },
    { label: 'RTB ≤ 10', pass: rtb == null ? null : rtb <= 10, value: rtb, rule: 'Veber' },
  ]

  const lipinski = checks.filter((c) => c.rule === 'Lipinski')
  const veber = checks.filter((c) => c.rule === 'Veber')
  const lipFails = lipinski.filter((c) => c.pass === false).length
  const veberFails = veber.filter((c) => c.pass === false).length
  const anyFilled = checks.some((c) => c.value != null)

  const fields = [
    { k: 'mw', label: 'MW (Da)', placeholder: 'ex: 234.5' },
    { k: 'alogp', label: 'ALogP', placeholder: 'ex: 2.1' },
    { k: 'hbd', label: 'HBD', placeholder: 'ex: 2' },
    { k: 'hba', label: 'HBA', placeholder: 'ex: 5' },
    { k: 'psa', label: 'PSA (Å²)', placeholder: 'ex: 65' },
    { k: 'rtb', label: 'RTB', placeholder: 'ex: 3' },
  ]

  return (
    <div className="space-y-4">
      <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
        {fields.map((f) => (
          <div key={f.k}>
            <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">{f.label}</label>
            <input
              className="glass-input w-full"
              type="number"
              step="any"
              placeholder={f.placeholder}
              value={vals[f.k]}
              onChange={(e) => setVals((p) => ({ ...p, [f.k]: e.target.value }))}
            />
          </div>
        ))}
      </div>

      {anyFilled ? (
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {lipFails === 0 ? <ShieldCheck size={16} className="text-green-700" /> : <ShieldAlert size={16} className="text-rose-600" />}
                <span className="text-sm font-semibold text-gray-800">Regra de Lipinski (Rule of 5)</span>
              </div>
              <Pill className={lipFails === 0 ? 'bg-green-100 text-green-800 border-green-300' : 'bg-rose-100 text-rose-700 border-rose-300'}>
                {lipFails === 0 ? 'OK' : `${lipFails} viol.`}
              </Pill>
            </div>
            <ul className="space-y-1.5">
              {lipinski.map((c) => (
                <li key={c.label} className="flex items-center justify-between text-xs">
                  <span className="text-gray-700">{c.label}</span>
                  <span className={`font-mono ${c.pass === null ? 'text-gray-400' : c.pass ? 'text-green-700' : 'text-rose-600'}`}>
                    {c.pass === null ? '—' : c.pass ? `✓ ${c.value}` : `✗ ${c.value}`}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {veberFails === 0 ? <ShieldCheck size={16} className="text-green-700" /> : <ShieldAlert size={16} className="text-rose-600" />}
                <span className="text-sm font-semibold text-gray-800">Regra de Veber (biodisponibilidade oral)</span>
              </div>
              <Pill className={veberFails === 0 ? 'bg-green-100 text-green-800 border-green-300' : 'bg-rose-100 text-rose-700 border-rose-300'}>
                {veberFails === 0 ? 'OK' : `${veberFails} viol.`}
              </Pill>
            </div>
            <ul className="space-y-1.5">
              {veber.map((c) => (
                <li key={c.label} className="flex items-center justify-between text-xs">
                  <span className="text-gray-700">{c.label}</span>
                  <span className={`font-mono ${c.pass === null ? 'text-gray-400' : c.pass ? 'text-green-700' : 'text-rose-600'}`}>
                    {c.pass === null ? '—' : c.pass ? `✓ ${c.value}` : `✗ ${c.value}`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="rounded-xl bg-gray-50 border border-gray-200 p-4 text-xs text-neutral-500">
          Preencha qualquer um dos campos acima para avaliar a druglikeness.
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Tool 2 — pChEMBL ↔ IC50/Ki converter
// ─────────────────────────────────────────────────────────────

function PChemblConverter() {
  const [pchembl, setPchembl] = useState('7')
  const [concentration, setConcentration] = useState('100')
  const [unit, setUnit] = useState('nM')

  const unitFactor = { M: 1, mM: 1e-3, uM: 1e-6, nM: 1e-9, pM: 1e-12 }

  const pVal = Number(pchembl)
  const ic50_M = Number.isFinite(pVal) ? Math.pow(10, -pVal) : null
  const ic50_nM = ic50_M != null ? ic50_M * 1e9 : null

  const concVal = Number(concentration)
  const concInM = Number.isFinite(concVal) ? concVal * unitFactor[unit] : null
  const computedP = concInM && concInM > 0 ? -Math.log10(concInM) : null

  const potencyLabel = (p) => {
    if (p == null || !Number.isFinite(p)) return { label: '—', color: 'text-gray-500' }
    if (p >= 9) return { label: 'Sub-nM (extremamente potente)', color: 'text-green-700' }
    if (p >= 7) return { label: 'Drug-like (< 100 nM)', color: 'text-green-700' }
    if (p >= 5) return { label: 'Moderado (µM)', color: 'text-amber-700' }
    return { label: 'Fraco (> 10 µM)', color: 'text-rose-700' }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <ArrowRightLeft size={14} className="text-green-700" />
          <span className="text-sm font-semibold text-gray-800">pChEMBL → IC₅₀ / Kᵢ</span>
        </div>
        <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">
          Valor pChEMBL (0–14)
        </label>
        <input
          className="glass-input w-full mb-3"
          type="number" step="0.1" min="0" max="14"
          value={pchembl}
          onChange={(e) => setPchembl(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">IC₅₀</p>
            <p className="text-lg font-bold text-gray-800 font-mono">
              {ic50_nM != null ? (ic50_nM >= 1000 ? `${(ic50_nM / 1000).toFixed(2)} µM` : `${ic50_nM.toFixed(2)} nM`) : '—'}
            </p>
          </div>
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Em M</p>
            <p className="text-lg font-bold text-gray-800 font-mono">
              {ic50_M != null ? ic50_M.toExponential(2) : '—'}
            </p>
          </div>
        </div>
        <p className={`mt-3 text-xs font-medium ${potencyLabel(pVal).color}`}>
          {potencyLabel(pVal).label}
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <ArrowRightLeft size={14} className="text-green-700" />
          <span className="text-sm font-semibold text-gray-800">IC₅₀ / Kᵢ → pChEMBL</span>
        </div>
        <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">
          Concentração
        </label>
        <div className="flex gap-2 mb-3">
          <input
            className="glass-input flex-1"
            type="number" step="any" min="0"
            value={concentration}
            onChange={(e) => setConcentration(e.target.value)}
          />
          <select className="glass-input w-24" value={unit} onChange={(e) => setUnit(e.target.value)}>
            {Object.keys(unitFactor).map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">pChEMBL</p>
            <p className="text-lg font-bold text-gray-800 font-mono">
              {computedP != null ? computedP.toFixed(2) : '—'}
            </p>
          </div>
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Em M</p>
            <p className="text-lg font-bold text-gray-800 font-mono">
              {concInM != null ? concInM.toExponential(2) : '—'}
            </p>
          </div>
        </div>
        <p className={`mt-3 text-xs font-medium ${potencyLabel(computedP).color}`}>
          {potencyLabel(computedP).label}
        </p>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Tool 3 — Calculadora de fórmula molecular
// ─────────────────────────────────────────────────────────────

// Pesos atômicos (Da) — IUPAC 2021, principais elementos orgânicos
const ATOMIC_WEIGHTS = {
  H: 1.008, He: 4.0026, Li: 6.94, Be: 9.0122, B: 10.81, C: 12.011, N: 14.007,
  O: 15.999, F: 18.998, Ne: 20.180, Na: 22.990, Mg: 24.305, Al: 26.982,
  Si: 28.085, P: 30.974, S: 32.06, Cl: 35.45, Ar: 39.948, K: 39.098,
  Ca: 40.078, Br: 79.904, I: 126.90, Fe: 55.845, Zn: 65.38, Cu: 63.546,
  Mn: 54.938, Se: 78.971, As: 74.922, Hg: 200.59, Pt: 195.08, Au: 196.97,
  Ag: 107.87, Pd: 106.42, Ni: 58.693, Co: 58.933,
}

function parseFormula(formula) {
  if (!formula) return { atoms: {}, valid: true, error: null }
  const re = /([A-Z][a-z]?)(\d*)/g
  const atoms = {}
  let consumed = 0
  let m
  while ((m = re.exec(formula)) !== null) {
    if (!m[1]) continue
    const el = m[1]
    const n = m[2] === '' ? 1 : parseInt(m[2], 10)
    if (!ATOMIC_WEIGHTS[el]) {
      return { atoms: {}, valid: false, error: `Elemento desconhecido: ${el}` }
    }
    atoms[el] = (atoms[el] || 0) + n
    consumed += m[0].length
  }
  if (consumed !== formula.replace(/\s/g, '').length) {
    return { atoms: {}, valid: false, error: 'Fórmula com caracteres inválidos' }
  }
  return { atoms, valid: true, error: null }
}

function FormulaCalculator() {
  const [formula, setFormula] = useState('C9H8O4')

  const parsed = useMemo(() => parseFormula(formula.trim()), [formula])

  const result = useMemo(() => {
    if (!parsed.valid) return null
    const atoms = parsed.atoms
    const mw = Object.entries(atoms).reduce((sum, [el, n]) => sum + ATOMIC_WEIGHTS[el] * n, 0)
    const heavy = Object.entries(atoms)
      .filter(([el]) => el !== 'H')
      .reduce((sum, [, n]) => sum + n, 0)
    const totalAtoms = Object.values(atoms).reduce((a, b) => a + b, 0)
    return { mw, heavy, totalAtoms, atoms }
  }, [parsed])

  return (
    <div className="space-y-3">
      <div>
        <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">
          Fórmula molecular
        </label>
        <input
          className="glass-input w-full font-mono"
          placeholder="ex: C9H8O4 (aspirina), C8H10N4O2 (cafeína)"
          value={formula}
          onChange={(e) => setFormula(e.target.value)}
        />
      </div>

      {!parsed.valid ? (
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
          {parsed.error}
        </div>
      ) : result && result.totalAtoms > 0 ? (
        <>
          <div className="grid gap-2 grid-cols-2 lg:grid-cols-3">
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
              <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">MW</p>
              <p className="text-lg font-bold text-gray-800 font-mono">{result.mw.toFixed(3)} Da</p>
            </div>
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
              <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Heavy atoms</p>
              <p className="text-lg font-bold text-gray-800 font-mono">{result.heavy}</p>
            </div>
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
              <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Átomos totais</p>
              <p className="text-lg font-bold text-gray-800 font-mono">{result.totalAtoms}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(result.atoms).map(([el, n]) => (
              <span key={el} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-green-50 border border-green-200 text-xs">
                <span className="font-semibold text-green-800 font-mono">{el}</span>
                <span className="text-gray-600">×{n}</span>
                <span className="text-gray-400 text-[10px]">({(ATOMIC_WEIGHTS[el] * n).toFixed(2)} Da)</span>
              </span>
            ))}
          </div>
        </>
      ) : null}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Tool 4 — Conversor de concentração / diluição
// ─────────────────────────────────────────────────────────────

function DilutionCalculator() {
  const [c1, setC1] = useState('10')
  const [u1, setU1] = useState('mM')
  const [c2, setC2] = useState('100')
  const [u2, setU2] = useState('uM')
  const [v2, setV2] = useState('1')
  const [vu, setVu] = useState('mL')

  const unitFactor = { M: 1, mM: 1e-3, uM: 1e-6, nM: 1e-9, pM: 1e-12 }
  const volFactor = { L: 1, mL: 1e-3, uL: 1e-6 }

  const C1_M = Number(c1) * (unitFactor[u1] ?? 1)
  const C2_M = Number(c2) * (unitFactor[u2] ?? 1)
  const V2_L = Number(v2) * (volFactor[vu] ?? 1)

  const V1_L = C1_M > 0 ? (C2_M * V2_L) / C1_M : null
  const valid = Number.isFinite(V1_L) && V1_L > 0 && C2_M < C1_M
  const errMsg = !Number.isFinite(V1_L) ? 'Preencha todos os campos com números válidos.'
    : C2_M >= C1_M ? 'A concentração final (C₂) deve ser MENOR que a inicial (C₁).'
    : null

  const displayV1 = (vL) => {
    if (!Number.isFinite(vL)) return '—'
    if (vL >= 1) return `${vL.toFixed(3)} L`
    if (vL >= 1e-3) return `${(vL * 1e3).toFixed(3)} mL`
    return `${(vL * 1e6).toFixed(2)} µL`
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-neutral-500">
        Fórmula <code className="font-mono">C₁V₁ = C₂V₂</code> — informe estoque, alvo e volume final.
      </p>
      <div className="grid gap-3 lg:grid-cols-3">
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">C₁ — estoque</label>
          <div className="flex gap-2">
            <input className="glass-input flex-1" type="number" step="any" min="0"
              value={c1} onChange={(e) => setC1(e.target.value)} />
            <select className="glass-input w-20" value={u1} onChange={(e) => setU1(e.target.value)}>
              {Object.keys(unitFactor).map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">C₂ — desejada</label>
          <div className="flex gap-2">
            <input className="glass-input flex-1" type="number" step="any" min="0"
              value={c2} onChange={(e) => setC2(e.target.value)} />
            <select className="glass-input w-20" value={u2} onChange={(e) => setU2(e.target.value)}>
              {Object.keys(unitFactor).map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">V₂ — volume final</label>
          <div className="flex gap-2">
            <input className="glass-input flex-1" type="number" step="any" min="0"
              value={v2} onChange={(e) => setV2(e.target.value)} />
            <select className="glass-input w-20" value={vu} onChange={(e) => setVu(e.target.value)}>
              {Object.keys(volFactor).map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>
      </div>

      {errMsg ? (
        <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">{errMsg}</div>
      ) : (
        <div className="grid gap-2 grid-cols-2">
          <div className="rounded-lg bg-green-50 border border-green-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-green-700 font-semibold mb-1">V₁ — estoque a pipetar</p>
            <p className="text-lg font-bold text-green-800 font-mono">{valid ? displayV1(V1_L) : '—'}</p>
          </div>
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Diluente a adicionar</p>
            <p className="text-lg font-bold text-gray-800 font-mono">{valid ? displayV1(V2_L - V1_L) : '—'}</p>
          </div>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Tool 5 — Ligand Efficiency
// ─────────────────────────────────────────────────────────────

function LigandEfficiency() {
  const [pchembl, setPchembl] = useState('7')
  const [heavyAtoms, setHeavyAtoms] = useState('25')
  const [mw, setMw] = useState('350')
  const [psa, setPsa] = useState('60')

  const p = Number(pchembl)
  const ha = Number(heavyAtoms)
  const mwN = Number(mw)
  const psaN = Number(psa)

  // LE = 1.37 × pIC50 / HA  (kcal/mol per heavy atom)
  const LE = Number.isFinite(p) && ha > 0 ? (1.37 * p) / ha : null
  // LLE = pIC50 - ALogP — not available, but we approximate using logP-like missing → skip
  // BEI = pIC50 / (MW/1000)  →  pIC50 × 1000 / MW
  const BEI = Number.isFinite(p) && mwN > 0 ? (p * 1000) / mwN : null
  // SEI = pIC50 × 100 / PSA
  const SEI = Number.isFinite(p) && psaN > 0 ? (p * 100) / psaN : null

  const fmt = (v, d = 2) => (v == null || !Number.isFinite(v) ? '—' : v.toFixed(d))

  const leLabel = (v) => {
    if (v == null) return { label: '—', color: 'text-gray-500' }
    if (v >= 0.4) return { label: 'Excelente (≥ 0.4)', color: 'text-green-700' }
    if (v >= 0.3) return { label: 'Bom (≥ 0.3)', color: 'text-green-700' }
    if (v >= 0.2) return { label: 'Moderado', color: 'text-amber-700' }
    return { label: 'Baixo', color: 'text-rose-700' }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-neutral-500">
        Métricas de eficiência ligante — normalizam potência por tamanho/polaridade para comparar candidatos fairly.
      </p>
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">pChEMBL</label>
          <input className="glass-input w-full" type="number" step="0.1" min="0" max="14"
            value={pchembl} onChange={(e) => setPchembl(e.target.value)} />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">Heavy atoms</label>
          <input className="glass-input w-full" type="number" step="1" min="1"
            value={heavyAtoms} onChange={(e) => setHeavyAtoms(e.target.value)} />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">MW (Da)</label>
          <input className="glass-input w-full" type="number" step="1" min="0"
            value={mw} onChange={(e) => setMw(e.target.value)} />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold block mb-1">PSA (Å²)</label>
          <input className="glass-input w-full" type="number" step="1" min="0"
            value={psa} onChange={(e) => setPsa(e.target.value)} />
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">LE — Ligand Efficiency</p>
          <p className="text-xl font-bold text-gray-800 font-mono">{fmt(LE, 3)}</p>
          <p className="text-[10px] text-gray-500 mt-1">1.37 × pIC₅₀ / HA</p>
          <p className={`text-[11px] font-medium mt-1 ${leLabel(LE).color}`}>{leLabel(LE).label}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">BEI — Binding Efficiency</p>
          <p className="text-xl font-bold text-gray-800 font-mono">{fmt(BEI, 2)}</p>
          <p className="text-[10px] text-gray-500 mt-1">pIC₅₀ × 1000 / MW</p>
          <p className="text-[11px] text-gray-600 mt-1">Alvo: ≥ 27 (drug-like)</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">SEI — Surface Efficiency</p>
          <p className="text-xl font-bold text-gray-800 font-mono">{fmt(SEI, 2)}</p>
          <p className="text-[10px] text-gray-500 mt-1">pIC₅₀ × 100 / PSA</p>
          <p className="text-[11px] text-gray-600 mt-1">Alvo: ≥ 18</p>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────

export default function ToolsPage() {
  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="animate-fade-in-up">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-green-700 mb-2">Tools</p>
        <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-gray-800">
          Ferramentas <span className="bg-gradient-to-br from-green-600 to-green-900 text-transparent bg-clip-text">Químicas</span>
        </h1>
        <p className="mt-2 text-sm text-neutral-600">
          Calculadoras locais para druglikeness, potência, fórmula molecular, diluição e eficiência ligante.
        </p>
      </div>

      {/* Quick guide */}
      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
        {[
          { icon: FlaskConical, label: 'Druglikeness', desc: 'Lipinski + Veber' },
          { icon: Zap, label: 'Potência', desc: 'pChEMBL ↔ IC₅₀' },
          { icon: Atom, label: 'Fórmula', desc: 'MW e composição' },
          { icon: Beaker, label: 'Diluição', desc: 'C₁V₁ = C₂V₂' },
          { icon: Sigma, label: 'Eficiência', desc: 'LE / BEI / SEI' },
        ].map((t, i) => (
          <div
            key={t.label}
            className="rounded-xl bg-white border-t-4 border-x border-b border-[#5c8d2f] border-gray-200 p-3 shadow-sm animate-fade-in-up"
            style={{ animationDelay: `${i * 0.05}s` }}
          >
            <div className="flex items-center gap-2 mb-1">
              <t.icon size={14} className="text-green-700" />
              <span className="text-xs font-semibold text-gray-800">{t.label}</span>
            </div>
            <p className="text-[11px] text-neutral-500">{t.desc}</p>
          </div>
        ))}
      </div>

      {/* Tool 1 */}
      <Section title="Druglikeness — Lipinski + Veber" delay={0.1}>
        <div className="flex items-center gap-2 mb-4 text-gray-500">
          <FlaskConical size={14} />
          <span className="text-xs">
            Avalia se um composto satisfaz as regras clássicas de biodisponibilidade oral.
          </span>
        </div>
        <LipinskiChecker />
      </Section>

      {/* Tool 2 */}
      <Section title="Conversor pChEMBL ↔ IC₅₀ / Kᵢ" delay={0.15}>
        <div className="flex items-center gap-2 mb-4 text-gray-500">
          <Zap size={14} />
          <span className="text-xs">
            pChEMBL = −log₁₀(C em M). pChEMBL ≥ 7 corresponde a IC₅₀ &lt; 100 nM (potência drug-like).
          </span>
        </div>
        <PChemblConverter />
      </Section>

      {/* Tool 3 */}
      <Section title="Calculadora de fórmula molecular" delay={0.2}>
        <div className="flex items-center gap-2 mb-4 text-gray-500">
          <Atom size={14} />
          <span className="text-xs">
            Soma os pesos atômicos (IUPAC 2021) e quantifica heavy atoms e composição elementar.
          </span>
        </div>
        <FormulaCalculator />
      </Section>

      {/* Tool 4 */}
      <Section title="Calculadora de diluição" delay={0.25}>
        <div className="flex items-center gap-2 mb-4 text-gray-500">
          <Beaker size={14} />
          <span className="text-xs">Preparo de soluções de trabalho a partir de um estoque concentrado.</span>
        </div>
        <DilutionCalculator />
      </Section>

      {/* Tool 5 */}
      <Section title="Métricas de eficiência ligante" delay={0.3}>
        <div className="flex items-center gap-2 mb-4 text-gray-500">
          <Sigma size={14} />
          <span className="text-xs">
            LE (kcal/mol/HA), BEI (potência por peso) e SEI (potência por área polar) — para comparar leads.
          </span>
        </div>
        <LigandEfficiency />
      </Section>

      {/* Disclaimer */}
      <Section title="Sobre estas ferramentas" delay={0.35}>
        <div className="grid gap-3 lg:grid-cols-2 text-xs text-neutral-600">
          <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Calculator size={12} className="text-green-700" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-700">Cálculos locais</span>
            </div>
            <p>
              Todos os cálculos rodam no navegador — nenhum dado é enviado ao backend. Resultados são determinísticos
              e não dependem do banco. Útil para análises pontuais durante exploração de compostos.
            </p>
          </div>
          <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Scale size={12} className="text-amber-600" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-700">Limitações</span>
            </div>
            <p>
              Lipinski/Veber são heurísticas — moléculas fora das regras (peptídeos, PROTACs, NPs) podem ser viáveis.
              pChEMBL aglutina IC₅₀/Kᵢ/EC₅₀; verifique o tipo do ensaio antes de comparar.
            </p>
          </div>
        </div>
      </Section>
    </div>
  )
}
