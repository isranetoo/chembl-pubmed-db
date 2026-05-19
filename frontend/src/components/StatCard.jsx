import { formatNumber } from '../lib/utils'

export default function StatCard({ label, value, helper, icon: Icon, color = 'emerald', delay = 0 }) {
  const borderColorMap = {
    emerald: 'border-t-[#5c8d2f]',
    sky:     'border-t-sky-500',
    amber:   'border-t-amber-500',
    violet:  'border-t-violet-500',
    rose:    'border-t-rose-500',
    teal:    'border-t-teal-500',
  }
  const iconBgMap = {
    emerald: 'from-green-600 to-green-900',
    sky:     'from-sky-500 to-sky-700',
    amber:   'from-amber-500 to-amber-700',
    violet:  'from-violet-500 to-violet-700',
    rose:    'from-rose-500 to-rose-700',
    teal:    'from-teal-500 to-teal-700',
  }
  const textColorMap = {
    emerald: 'text-green-800',
    sky:     'text-sky-700',
    amber:   'text-amber-700',
    violet:  'text-violet-700',
    rose:    'text-rose-700',
    teal:    'text-teal-700',
  }

  return (
    <div
      className={`animate-fade-in-up relative overflow-hidden rounded-xl bg-white border border-gray-200 border-t-4 ${borderColorMap[color]} p-5 shadow-md transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5`}
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">{label}</p>
          <p className={`text-3xl font-bold tracking-tight ${textColorMap[color]}`}>
            {formatNumber(value)}
          </p>
          {helper && <p className="mt-2 text-xs text-neutral-500">{helper}</p>}
        </div>
        {Icon && (
          <div
            className={`w-10 h-10 rounded-xl bg-gradient-to-br ${iconBgMap[color]} flex items-center justify-center shadow-md`}
          >
            <Icon size={18} className="text-white" />
          </div>
        )}
      </div>
    </div>
  )
}
