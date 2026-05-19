import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Boxes, ExternalLink, Loader2, RotateCcw, AlertTriangle, Camera,
  MousePointerClick, Beaker, Layers, Target as TargetIcon,
} from 'lucide-react'

// ── 3Dmol.js loader (lazy, singleton) ──────────────────────────
const SCRIPT_URL = 'https://3Dmol.csb.pitt.edu/build/3Dmol-min.js'
let _loaderPromise = null

function load3Dmol() {
  if (typeof window !== 'undefined' && window.$3Dmol) return Promise.resolve(window.$3Dmol)
  if (_loaderPromise) return _loaderPromise
  _loaderPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${SCRIPT_URL}"]`)
    if (existing) {
      existing.addEventListener('load', () => resolve(window.$3Dmol))
      existing.addEventListener('error', reject)
      return
    }
    const script = document.createElement('script')
    script.src = SCRIPT_URL
    script.async = true
    script.onload = () => resolve(window.$3Dmol)
    script.onerror = () => reject(new Error('Falha ao carregar 3Dmol.js'))
    document.head.appendChild(script)
  })
  return _loaderPromise
}

// ── RCSB metadata fetch ────────────────────────────────────────
async function fetchRcsbMeta(pdbId) {
  try {
    const r = await fetch(`https://data.rcsb.org/rest/v1/core/entry/${pdbId}`)
    if (!r.ok) return null
    const data = await r.json()
    return {
      title: data?.struct?.title,
      method: data?.exptl?.[0]?.method,
      resolution: data?.rcsb_entry_info?.resolution_combined?.[0],
      deposited: data?.rcsb_accession_info?.deposit_date?.slice(0, 10),
      released: data?.rcsb_accession_info?.initial_release_date?.slice(0, 10),
      polymer_count: data?.rcsb_entry_info?.polymer_entity_count_protein,
      ligand_count: data?.rcsb_entry_info?.deposited_nonpolymer_entity_instance_count,
    }
  } catch {
    return null
  }
}

// HET groups que tipicamente são buffer/solvente — escondemos do
// "Ligand explorer" pra não poluir. Usuário ainda pode ver via "show all".
const BUFFER_HET = new Set([
  'HOH', 'DOD', 'WAT', // água
  'SO4', 'PO4', 'NO3', 'CO3', 'CL', 'BR', 'IOD', // íons/ânions simples
  'EDO', 'GOL', 'MPD', 'PEG', 'PG4', 'PEU', // crio-protetores e PEGs
  'ACT', 'FMT', 'ACE', 'EPE', 'TRS', 'BTB', // buffers
  'DMS', 'DMF', // solventes
])

const REPRESENTATIONS = [
  { key: 'cartoon', label: 'Cartoon' },
  { key: 'stick', label: 'Sticks' },
  { key: 'sphere', label: 'Sphere' },
  { key: 'line', label: 'Line' },
]

const COLOR_SCHEMES = [
  { key: 'spectrum', label: 'Spectrum' },
  { key: 'chain', label: 'Chain' },
  { key: 'ssJmol', label: 'SS' },
]

function styleSpec(rep, color) {
  const colorMap = {
    spectrum: { color: 'spectrum' },
    chain: { colorscheme: 'chainHetatm' },
    ssJmol: { colorscheme: 'ssJmol' },
  }
  return { [rep]: { ...(colorMap[color] || colorMap.spectrum) } }
}

// ── Viewer component ───────────────────────────────────────────
export default function PdbViewer({ pdbId, height = 480, compact = false }) {
  const containerRef = useRef(null)
  const viewerRef = useRef(null)
  const surfaceHandleRef = useRef(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [meta, setMeta] = useState(null)

  const [rep, setRep] = useState('cartoon')
  const [color, setColor] = useState('spectrum')
  const [spin, setSpin] = useState(false)
  const [showLigands, setShowLigands] = useState(true)
  const [showSurface, setShowSurface] = useState(false)
  const [surfaceOpacity, setSurfaceOpacity] = useState(0.6)

  const [ligands, setLigands] = useState([])       // [{key, resn, resi, chain, atomCount}]
  const [highlightLigand, setHighlightLigand] = useState(null)  // key
  const [showBuffers, setShowBuffers] = useState(false)
  const [selectedAtom, setSelectedAtom] = useState(null)

  // (Re)build the viewer whenever pdbId changes
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setMeta(null)
    setLigands([])
    setHighlightLigand(null)
    setSelectedAtom(null)
    surfaceHandleRef.current = null

    Promise.all([
      load3Dmol(),
      fetch(`https://files.rcsb.org/download/${pdbId}.pdb`).then((r) => {
        if (!r.ok) throw new Error(`PDB ${pdbId} não encontrado no RCSB`)
        return r.text()
      }),
      fetchRcsbMeta(pdbId),
    ])
      .then(([$3Dmol, pdbData, rcsbMeta]) => {
        if (cancelled) return
        // Tear down previous viewer
        if (viewerRef.current) {
          try { viewerRef.current.clear() } catch { /* noop */ }
          viewerRef.current = null
        }
        const el = containerRef.current
        if (!el) return
        el.innerHTML = ''
        const viewer = $3Dmol.createViewer(el, {
          backgroundColor: '#f9fafb',
          antialias: true,
        })
        viewer.addModel(pdbData, 'pdb')
        viewer.setStyle({}, styleSpec(rep, color))
        if (showLigands) {
          viewer.addStyle({ hetflag: true }, { stick: { colorscheme: 'orangeCarbon', radius: 0.18 } })
        }

        // Extrai ligantes (HET groups, deduplicados por chain:resi:resn)
        const hetAtoms = viewer.getModel(0).selectedAtoms({ hetflag: true }) || []
        const ligMap = new Map()
        hetAtoms.forEach((a) => {
          if (!a.resn) return
          const key = `${a.chain}:${a.resi}:${a.resn}`
          if (!ligMap.has(key)) {
            ligMap.set(key, { key, resn: a.resn, resi: a.resi, chain: a.chain, atomCount: 0 })
          }
          ligMap.get(key).atomCount += 1
        })
        const ligList = Array.from(ligMap.values())
          .sort((a, b) => b.atomCount - a.atomCount)

        // Atomic click handler
        viewer.setClickable({}, true, (atom) => {
          if (!atom) return
          setSelectedAtom({
            chain: atom.chain,
            resn: atom.resn,
            resi: atom.resi,
            atom: atom.atom,
            elem: atom.elem,
            hetflag: !!atom.hetflag,
            x: atom.x, y: atom.y, z: atom.z,
          })
        })

        viewer.zoomTo()
        viewer.render()
        if (spin) viewer.spin('y', 1)

        viewerRef.current = viewer
        setLigands(ligList)
        // Auto-destaca o ligante principal (maior HET fora de buffers)
        const primary = ligList.find((l) => !BUFFER_HET.has(l.resn))
        if (primary) setHighlightLigand(primary.key)
        setMeta(rcsbMeta)
        setLoading(false)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err.message || String(err))
        setLoading(false)
      })

    return () => {
      cancelled = true
      if (viewerRef.current) {
        try { viewerRef.current.clear() } catch { /* noop */ }
        viewerRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pdbId])

  // Re-aplica estilos (representação/cor/ligantes/highlight) sem refetch
  const rebuildStyles = () => {
    const v = viewerRef.current
    if (!v) return
    v.setStyle({}, styleSpec(rep, color))
    if (showLigands) {
      v.addStyle({ hetflag: true }, { stick: { colorscheme: 'orangeCarbon', radius: 0.18 } })
    }
    // Highlight do ligante selecionado
    if (highlightLigand) {
      const [chain, resi, resn] = highlightLigand.split(':')
      v.addStyle({ chain, resi: Number(resi), resn }, {
        stick: { color: '#16a34a', radius: 0.28 },
        sphere: { color: '#16a34a', radius: 0.4, opacity: 0.35 },
      })
    }
    // Highlight do átomo/resíduo clicado
    if (selectedAtom) {
      v.addStyle({ chain: selectedAtom.chain, resi: selectedAtom.resi }, {
        stick: { color: '#dc2626', radius: 0.24 },
      })
    }
    v.render()
  }

  useEffect(() => {
    rebuildStyles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rep, color, showLigands, highlightLigand, selectedAtom])

  // Rotação
  useEffect(() => {
    const v = viewerRef.current
    if (!v) return
    if (spin) v.spin('y', 1)
    else v.spin(false)
  }, [spin])

  // Surface toggle + opacidade
  useEffect(() => {
    const v = viewerRef.current
    if (!v || !window.$3Dmol) return
    // Remove surfaces existentes
    try { v.removeAllSurfaces() } catch { /* noop */ }
    surfaceHandleRef.current = null
    if (showSurface) {
      try {
        const handle = v.addSurface(
          window.$3Dmol.SurfaceType.VDW,
          { opacity: surfaceOpacity, color: 'white' },
          { hetflag: false },  // só a proteína
        )
        surfaceHandleRef.current = handle
      } catch { /* noop */ }
    }
    v.render()
  }, [showSurface, surfaceOpacity])

  // Zoom no ligante quando selecionado
  useEffect(() => {
    const v = viewerRef.current
    if (!v || !highlightLigand) return
    const [chain, resi, resn] = highlightLigand.split(':')
    try {
      v.zoomTo({ chain, resi: Number(resi), resn })
      v.zoom(0.6)
      v.render()
    } catch { /* noop */ }
  }, [highlightLigand])

  const resetView = () => {
    const v = viewerRef.current
    if (!v) return
    v.zoomTo()
    v.render()
  }

  const screenshot = () => {
    const v = viewerRef.current
    if (!v) return
    const dataUrl = v.pngURI()
    const a = document.createElement('a')
    a.href = dataUrl
    a.download = `${pdbId}.png`
    a.click()
  }

  const visibleLigands = useMemo(
    () => ligands.filter((l) => showBuffers || !BUFFER_HET.has(l.resn)),
    [ligands, showBuffers],
  )

  return (
    <div className="rounded-2xl bg-white border border-gray-200 shadow-card overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 bg-gray-50 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <Boxes size={14} className="text-cyan-700" />
            <code className="text-sm font-mono font-bold text-gray-800">{pdbId}</code>
            {meta?.method && (
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-cyan-100 text-cyan-800 border border-cyan-200 font-semibold">
                {meta.method}
              </span>
            )}
            {meta?.resolution != null && (
              <span className="text-[10px] text-gray-500 font-mono">{meta.resolution.toFixed(2)} Å</span>
            )}
          </div>
          {meta?.title && (
            <p className="text-xs text-gray-600 truncate max-w-xl" title={meta.title}>{meta.title}</p>
          )}
        </div>
        <a
          href={`https://www.rcsb.org/structure/${pdbId}`}
          target="_blank" rel="noopener noreferrer"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] border border-gray-200 bg-white hover:bg-green-50 hover:border-green-300 transition-colors"
        >
          RCSB <ExternalLink size={10} />
        </a>
      </div>

      {/* Controls */}
      <div className="border-b border-gray-200 px-4 py-2.5 flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center gap-1">
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mr-1">Estilo</span>
          {REPRESENTATIONS.map((r) => (
            <button
              key={r.key}
              onClick={() => setRep(r.key)}
              className={`px-2 py-1 rounded-md text-[11px] transition-colors ${
                rep === r.key ? 'bg-green-700 text-white' : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
        <div className="h-4 w-px bg-gray-200" />
        <div className="flex items-center gap-1">
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mr-1">Cor</span>
          {COLOR_SCHEMES.map((c) => (
            <button
              key={c.key}
              onClick={() => setColor(c.key)}
              className={`px-2 py-1 rounded-md text-[11px] transition-colors ${
                color === c.key ? 'bg-green-700 text-white' : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div className="h-4 w-px bg-gray-200" />
        <label className="inline-flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showLigands} onChange={(e) => setShowLigands(e.target.checked)}
            className="rounded border-gray-300 text-green-700 focus:ring-green-500" />
          <span className="text-gray-700">Ligantes</span>
        </label>
        <label className="inline-flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={spin} onChange={(e) => setSpin(e.target.checked)}
            className="rounded border-gray-300 text-green-700 focus:ring-green-500" />
          <span className="text-gray-700">Rotação</span>
        </label>
        <label className="inline-flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" checked={showSurface} onChange={(e) => setShowSurface(e.target.checked)}
            className="rounded border-gray-300 text-green-700 focus:ring-green-500" />
          <span className="text-gray-700 inline-flex items-center gap-1"><Layers size={11} /> Superfície</span>
        </label>
        {showSurface && (
          <input
            type="range" min="0.1" max="1" step="0.05"
            value={surfaceOpacity}
            onChange={(e) => setSurfaceOpacity(Number(e.target.value))}
            className="w-20 accent-green-700"
            title={`Opacidade: ${(surfaceOpacity * 100).toFixed(0)}%`}
          />
        )}
        <div className="ml-auto flex items-center gap-1">
          <button onClick={resetView} title="Reset"
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] bg-white border border-gray-200 text-gray-700 hover:bg-gray-50">
            <RotateCcw size={11} /> Reset
          </button>
          <button onClick={screenshot} title="Salvar PNG"
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] bg-white border border-gray-200 text-gray-700 hover:bg-gray-50">
            <Camera size={11} /> PNG
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="relative" style={{ height }}>
        <div ref={containerRef} className="w-full h-full" />
        {loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50/80 backdrop-blur-sm">
            <Loader2 size={24} className="text-green-700 animate-spin mb-2" />
            <p className="text-xs text-neutral-500">Carregando estrutura {pdbId}…</p>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-rose-50/90 p-6 text-center">
            <AlertTriangle size={24} className="text-rose-600 mb-2" />
            <p className="text-sm font-medium text-rose-700 mb-1">Não foi possível carregar a estrutura</p>
            <p className="text-xs text-rose-600 max-w-md">{error}</p>
          </div>
        )}

        {/* Selected residue overlay */}
        {selectedAtom && !loading && !error && (
          <div className="absolute top-3 left-3 max-w-[260px] rounded-xl bg-white/95 backdrop-blur border border-gray-200 shadow-md p-3 text-xs">
            <div className="flex items-center justify-between mb-1">
              <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-rose-600 font-semibold">
                <MousePointerClick size={11} /> Resíduo selecionado
              </span>
              <button
                onClick={() => setSelectedAtom(null)}
                className="text-gray-400 hover:text-gray-700 text-[11px]"
              >✕</button>
            </div>
            <p className="font-mono text-sm font-bold text-gray-800">
              {selectedAtom.resn}{selectedAtom.resi}
              <span className="text-gray-400 mx-1">·</span>
              chain {selectedAtom.chain}
            </p>
            <p className="text-[11px] text-gray-600 mt-1">
              Átomo <span className="font-mono">{selectedAtom.atom}</span> ({selectedAtom.elem})
              {selectedAtom.hetflag && <span className="ml-1 inline-block px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 text-[9px] font-semibold">HET</span>}
            </p>
            <p className="text-[10px] text-gray-400 mt-1 font-mono">
              ({selectedAtom.x?.toFixed(1)}, {selectedAtom.y?.toFixed(1)}, {selectedAtom.z?.toFixed(1)})
            </p>
          </div>
        )}
      </div>

      {/* Ligand explorer */}
      {!compact && ligands.length > 0 && (
        <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">
              <Beaker size={11} /> Heteroatoms ({visibleLigands.length}{!showBuffers && ligands.length > visibleLigands.length ? ` de ${ligands.length}` : ''})
            </div>
            {ligands.some((l) => BUFFER_HET.has(l.resn)) && (
              <label className="inline-flex items-center gap-1 text-[10px] text-gray-500 cursor-pointer">
                <input type="checkbox" checked={showBuffers} onChange={(e) => setShowBuffers(e.target.checked)}
                  className="rounded border-gray-300 text-green-700 focus:ring-green-500" />
                buffers/água
              </label>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {visibleLigands.map((lig) => {
              const isActive = lig.key === highlightLigand
              const isBuffer = BUFFER_HET.has(lig.resn)
              return (
                <button
                  key={lig.key}
                  onClick={() => setHighlightLigand(isActive ? null : lig.key)}
                  className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] border transition-all ${
                    isActive
                      ? 'bg-green-100 border-green-500 text-green-800 shadow-sm'
                      : isBuffer
                        ? 'bg-white border-gray-200 text-gray-500 hover:border-gray-300'
                        : 'bg-white border-gray-200 text-gray-700 hover:border-green-300 hover:bg-green-50'
                  }`}
                  title={`${lig.resn} · resi ${lig.resi} · chain ${lig.chain} · ${lig.atomCount} átomos`}
                >
                  {isActive && <TargetIcon size={10} />}
                  <span className="font-mono font-semibold">{lig.resn}</span>
                  <span className="text-[10px] opacity-60">{lig.chain}/{lig.resi}</span>
                  <span className="text-[9px] text-gray-400">{lig.atomCount}a</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Footer metadata */}
      {meta && !compact && (
        <div className="border-t border-gray-200 px-4 py-2 bg-gray-50 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-600">
          {meta.deposited && <span>Depósito: <span className="font-mono">{meta.deposited}</span></span>}
          {meta.released && <span>Release: <span className="font-mono">{meta.released}</span></span>}
          {meta.polymer_count != null && <span>Cadeias proteicas: <span className="font-mono">{meta.polymer_count}</span></span>}
          {meta.ligand_count != null && <span>Ligantes: <span className="font-mono">{meta.ligand_count}</span></span>}
        </div>
      )}
    </div>
  )
}
