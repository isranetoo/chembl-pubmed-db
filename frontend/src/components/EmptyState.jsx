import { SearchX } from 'lucide-react'

export default function EmptyState({
  title = 'Nada encontrado',
  description = 'Tente ajustar os filtros.',
  icon: Icon = SearchX,
}) {
  return (
    <div className="rounded-2xl bg-white border border-gray-200 shadow-card p-12 text-center animate-fade-in">
      <div className="w-14 h-14 rounded-2xl bg-green-50 border border-green-200 flex items-center justify-center mx-auto mb-4">
        <Icon size={24} className="text-green-700" />
      </div>
      <h3 className="text-base font-semibold text-gray-800 mb-1">{title}</h3>
      <p className="text-sm text-neutral-500">{description}</p>
    </div>
  )
}
