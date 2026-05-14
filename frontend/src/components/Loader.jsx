export default function Loader({ label = 'Carregando...' }) {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center gap-4 rounded-2xl glass p-10">
      <div className="relative w-10 h-10">
        <div className="absolute inset-0 rounded-full border-2 border-emerald-500/20" />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-emerald-400 animate-spin" />
      </div>
      <p className="text-sm text-white/40">{label}</p>
    </div>
  )
}
