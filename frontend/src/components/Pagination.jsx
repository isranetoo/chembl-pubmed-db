import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function Pagination({ page = 1, pages = 1, onPrevious, onNext }) {
  if (!pages || pages <= 1) return null
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white border border-gray-200 px-4 py-3 text-sm shadow-sm animate-fade-in">
      <p className="text-neutral-500">
        Página <span className="font-semibold text-gray-800">{page}</span> de{' '}
        <span className="font-semibold text-gray-800">{pages}</span>
      </p>
      <div className="flex items-center gap-2">
        <button
          onClick={onPrevious}
          disabled={page <= 1}
          className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 transition-all hover:border-[#5c8d2f] hover:text-green-800 hover:bg-green-50 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-white disabled:hover:text-gray-700 disabled:hover:border-gray-200"
        >
          <ChevronLeft size={14} /> Anterior
        </button>
        <button
          onClick={onNext}
          disabled={page >= pages}
          className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 transition-all hover:border-[#5c8d2f] hover:text-green-800 hover:bg-green-50 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-white disabled:hover:text-gray-700 disabled:hover:border-gray-200"
        >
          Próxima <ChevronRight size={14} />
        </button>
      </div>
    </div>
  )
}
