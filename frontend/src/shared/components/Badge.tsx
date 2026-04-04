type Variant = 'green' | 'amber' | 'red' | 'gray' | 'blue'

const VARIANT_CLASSES: Record<Variant, React.CSSProperties> = {
  green: { background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0' },
  amber: { background: '#fffbeb', color: '#92400e', border: '1px solid #fde68a' },
  red:   { background: '#fff1f2', color: '#991b1b', border: '1px solid #fecaca' },
  gray:  { background: '#f5f5f4', color: '#57534e', border: '1px solid #d6d3d1' },
  blue:  { background: '#eff6ff', color: '#1e40af', border: '1px solid #bfdbfe' },
}

interface BadgeProps {
  variant?: Variant
  children: React.ReactNode
  className?: string
}

export default function Badge({ variant = 'gray', children, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${className}`}
      style={{ ...VARIANT_CLASSES[variant], fontFamily: 'ui-sans-serif, system-ui, sans-serif' }}
    >
      {children}
    </span>
  )
}
