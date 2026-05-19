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
  if (p >= 4) return 'bg-green-100 text-green-800 border-green-300'
  if (p >= 3) return 'bg-sky-100 text-sky-800 border-sky-300'
  if (p >= 2) return 'bg-amber-100 text-amber-800 border-amber-300'
  return 'bg-gray-100 text-gray-700 border-gray-300'
}

export function getPhaseColor(phase) {
  const p = Number(phase)
  if (p >= 4) return '#2f6b14'
  if (p >= 3) return '#0369a1'
  if (p >= 2) return '#b45309'
  return '#64748b'
}
