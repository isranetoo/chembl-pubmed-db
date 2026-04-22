import { cn } from '../lib/utils'

export default function Pill({ children, className = '' }) {
  return (
    <span className={cn('inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium', className)}>
      {children}
    </span>
  )
}
