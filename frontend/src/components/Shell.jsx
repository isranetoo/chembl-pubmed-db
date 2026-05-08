export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-3xl space-y-3">
        {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-300">{eyebrow}</p> : null}
        <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">{title}</h1>
        {description ? <p className="text-sm leading-6 text-slate-400 md:text-base">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
    </div>
  )
}

export function Section({ title, description, children }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-soft backdrop-blur">
      {(title || description) && (
        <div className="mb-5 space-y-1">
          {title ? <h2 className="text-lg font-semibold text-white">{title}</h2> : null}
          {description ? <p className="text-sm text-slate-400">{description}</p> : null}
        </div>
      )}
      {children}
    </section>
  )
}
