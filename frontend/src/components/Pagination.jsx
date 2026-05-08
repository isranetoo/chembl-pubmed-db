export default function Pagination({ page = 1, pages = 1, onPrevious, onNext }) {
  if (!pages || pages <= 1) return null

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
      <p>
        Página <span className="font-semibold text-white">{page}</span> de{' '}
        <span className="font-semibold text-white">{pages}</span>
      </p>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onPrevious}
          disabled={page <= 1}
          className="rounded-xl border border-white/10 px-3 py-2 transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Anterior
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={page >= pages}
          className="rounded-xl border border-white/10 px-3 py-2 transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Próxima
        </button>
      </div>
    </div>
  )
}
