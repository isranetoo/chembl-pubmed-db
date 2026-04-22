export default function Loader({ label = 'Carregando...' }) {
  return (
    <div className="flex min-h-[180px] flex-col items-center justify-center gap-3 rounded-3xl border border-dashed border-white/10 bg-white/5 text-sm text-slate-400">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-brand-400" />
      <p>{label}</p>
    </div>
  )
}
