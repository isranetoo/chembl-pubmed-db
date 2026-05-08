import { formatNumber } from '../lib/utils'

export default function StatCard({ label, value, helper }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-5 shadow-soft">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-white">{formatNumber(value)}</p>
      {helper ? <p className="mt-2 text-xs text-slate-500">{helper}</p> : null}
    </div>
  )
}
