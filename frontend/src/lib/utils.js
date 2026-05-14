import clsx from 'clsx'

export function cn(...inputs) { return clsx(inputs) }

export function formatNumber(value, options = {}) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return new Intl.NumberFormat('pt-BR', options).format(Number(value))
}

export function phaseLabel(phase) {
  if (phase === null || phase === undefined) return '—'
  const p = Number(phase)
  if (p === 4) return 'Approved'
  if (p === 3) return 'Phase 3'
  if (p === 2) return 'Phase 2'
  if (p === 1) return 'Phase 1'
  if (p === 0.5) return 'Early Phase 1'
  return 'Preclinical'
}

export function getPhaseBadgeClass(phase) {
  const p = Number(phase)
  if (p >= 4) return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
  if (p >= 3) return 'bg-sky-500/15 text-sky-300 border-sky-500/30'
  if (p >= 2) return 'bg-amber-500/15 text-amber-300 border-amber-500/30'
  return 'bg-slate-500/15 text-slate-300 border-slate-500/30'
}

export function getPhaseColor(phase) {
  const p = Number(phase)
  if (p >= 4) return '#10b981'
  if (p >= 3) return '#3b82f6'
  if (p >= 2) return '#f59e0b'
  return '#64748b'
}
