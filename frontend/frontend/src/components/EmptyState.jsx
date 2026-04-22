export default function EmptyState({ title = 'Nada encontrado', description = 'Tente ajustar os filtros ou a consulta.' }) {
  return (
    <div className="rounded-3xl border border-dashed border-white/10 bg-white/5 p-10 text-center">
      <h3 className="text-lg font-medium text-white">{title}</h3>
      <p className="mt-2 text-sm text-slate-400">{description}</p>
    </div>
  )
}
