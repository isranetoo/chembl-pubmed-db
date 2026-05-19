import { useEffect, useRef, useState } from 'react'
import { Boxes, ExternalLink, Loader2, RotateCcw, AlertTriangle, Camera } from 'lucide-react'

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
export default function PdbViewer({ pdbId, height = 480 }) {
  const containerRef = useRef(null)
  const viewerRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [meta, setMeta] = useState(null)
  const [rep, setRep] = useState('cartoon')
  const [color, setColor] = useState('spectrum')
  const [spin, setSpin] = useState(false)
  const [showLigands, setShowLigands] = useState(true)

  // (Re)build the viewer whenever pdbId changes
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setMeta(null)

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
        // Tear down any previous viewer
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
        viewer.zoomTo()
        viewer.render()
        if (spin) viewer.spin('y', 1)
        viewerRef.current = viewer
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

  // Live restyle without re-fetching
  useEffect(() => {
    const v = viewerRef.current
    if (!v) return
    v.setStyle({}, styleSpec(rep, color))
    if (showLigands) {
      v.addStyle({ hetflag: true }, { stick: { colorscheme: 'orangeCarbon', radius: 0.18 } })
    }
    v.render()
  }, [rep, color, showLigands])

  useEffect(() => {
    const v = viewerRef.current
    if (!v) return
    if (spin) v.spin('y', 1)
    else v.spin(false)
  }, [spin])

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

  return (
    <div className="rounded-2xl bg-white border border-gray-200 shadow-card overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 bg-gray-50 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
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
        <div className="flex items-center gap-2">
          <a
            href={`https://www.rcsb.org/structure/${pdbId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] border border-gray-200 bg-white hover:bg-green-50 hover:border-green-300 transition-colors"
          >
            RCSB <ExternalLink size={10} />
          </a>
        </div>
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
                rep === r.key
                  ? 'bg-green-700 text-white'
                  : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
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
                color === c.key
                  ? 'bg-green-700 text-white'
                  : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
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
      </div>

      {/* Footer metadata */}
      {meta && (
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
