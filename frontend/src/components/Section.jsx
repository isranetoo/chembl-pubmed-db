export default function Section({ title, description, children, delay = 0, className = '' }) {
  return (
    <section className={`glass-card p-6 animate-fade-in-up ${className}`} style={{ animationDelay: `${delay}s` }}>
      {(title || description) && (
        <div className="mb-5 space-y-1">
          {title && <h2 className="text-lg font-bold text-white/90" style={{ fontFamily: 'Outfit' }}>{title}</h2>}
          {description && <p className="text-sm text-white/35">{description}</p>}
        </div>
      )}
      {children}
    </section>
  )
}
