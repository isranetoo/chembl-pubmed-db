import { SearchX } from 'lucide-react'

export default function EmptyState({ title = 'Nada encontrado', description = 'Tente ajustar os filtros.', icon: Icon = SearchX }) {
  return (
    <div className="rounded-2xl glass p-12 text-center animate-fade-in">
      <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mx-auto mb-4">
        <Icon size={24} className="text-white/20" />
      </div>
      <h3 className="text-base font-semibold text-white/70 mb-1" style={{ fontFamily: 'Outfit' }}>{title}</h3>
      <p className="text-sm text-white/30">{description}</p>
    </div>
  )
}
