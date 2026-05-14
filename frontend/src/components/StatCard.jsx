import { formatNumber } from '../lib/utils'

export default function StatCard({ label, value, helper, icon: Icon, color = 'emerald', delay = 0 }) {
  const colorMap = {
    emerald: 'from-emerald-500/20 to-emerald-600/5 border-emerald-500/15 shadow-emerald-500/5',
    sky: 'from-sky-500/20 to-sky-600/5 border-sky-500/15 shadow-sky-500/5',
    amber: 'from-amber-500/20 to-amber-600/5 border-amber-500/15 shadow-amber-500/5',
    violet: 'from-violet-500/20 to-violet-600/5 border-violet-500/15 shadow-violet-500/5',
    rose: 'from-rose-500/20 to-rose-600/5 border-rose-500/15 shadow-rose-500/5',
    teal: 'from-teal-500/20 to-teal-600/5 border-teal-500/15 shadow-teal-500/5',
  }
  const iconColorMap = {
    emerald: 'from-emerald-400 to-emerald-600',
    sky: 'from-sky-400 to-sky-600',
    amber: 'from-amber-400 to-amber-600',
    violet: 'from-violet-400 to-violet-600',
    rose: 'from-rose-400 to-rose-600',
    teal: 'from-teal-400 to-teal-600',
  }
  const textColor = {
    emerald: 'text-emerald-400', sky: 'text-sky-400', amber: 'text-amber-400',
    violet: 'text-violet-400', rose: 'text-rose-400', teal: 'text-teal-400',
  }

  return (
    <div
      className={`animate-fade-in-up relative overflow-hidden rounded-2xl bg-gradient-to-br ${colorMap[color]} border backdrop-blur-xl p-5 shadow-lg transition-all duration-300 hover:scale-[1.02] hover:shadow-xl`}
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-white/40 mb-3">{label}</p>
          <p className={`text-3xl font-bold tracking-tight ${textColor[color]}`} style={{ fontFamily: 'Outfit' }}>
            {formatNumber(value)}
          </p>
          {helper && <p className="mt-2 text-xs text-white/30">{helper}</p>}
        </div>
        {Icon && (
          <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${iconColorMap[color]} flex items-center justify-center shadow-lg`}>
            <Icon size={18} className="text-white" />
          </div>
        )}
      </div>
      {/* Decorative glow */}
      <div className={`absolute -bottom-8 -right-8 w-24 h-24 rounded-full bg-gradient-to-br ${iconColorMap[color]} opacity-[0.07] blur-2xl`} />
    </div>
  )
}
