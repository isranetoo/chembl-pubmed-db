export default function Section({ title, description, children, delay = 0, className = '' }) {
  return (
    <section
      className={`bg-white border border-gray-200 rounded-2xl shadow-card p-6 animate-fade-in-up ${className}`}
      style={{ animationDelay: `${delay}s` }}
    >
      {(title || description) && (
        <div className="mb-5 space-y-1">
          {title && <h2 className="text-lg font-semibold text-gray-800">{title}</h2>}
          {description && <p className="text-sm text-neutral-500">{description}</p>}
        </div>
      )}
      {children}
    </section>
  )
}
