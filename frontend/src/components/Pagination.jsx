import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function Pagination({ page = 1, pages = 1, onPrevious, onNext }) {
  if (!pages || pages <= 1) return null
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl glass px-4 py-3 text-sm animate-fade-in">
      <p className="text-white/40">
        Página <span className="font-semibold text-white/80">{page}</span> de{' '}
        <span className="font-semibold text-white/80">{pages}</span>
      </p>
      <div className="flex items-center gap-2">
        <button onClick={onPrevious} disabled={page <= 1}
          className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs font-medium transition-all hover:bg-white/[0.08] disabled:opacity-30 disabled:cursor-not-allowed">
          <ChevronLeft size={14} /> Anterior
        </button>
        <button onClick={onNext} disabled={page >= pages}
          className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs font-medium transition-all hover:bg-white/[0.08] disabled:opacity-30 disabled:cursor-not-allowed">
          Próxima <ChevronRight size={14} />
        </button>
      </div>
    </div>
  )
}
