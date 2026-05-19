export default function Loader({ label = 'Carregando...' }) {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center gap-4 rounded-2xl bg-white border border-gray-200 shadow-card p-10">
      <div className="relative w-10 h-10">
        <div className="absolute inset-0 rounded-full border-2 border-green-200" />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-green-700 animate-spin" />
      </div>
      <p className="text-sm text-neutral-500">{label}</p>
    </div>
  )
}
