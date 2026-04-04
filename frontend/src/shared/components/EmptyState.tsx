interface EmptyStateProps {
  title: string
  description?: string
  icon?: React.ReactNode
  action?: React.ReactNode
}

export default function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-40 text-center p-8 gap-3">
      {icon && <div style={{ color: 'var(--c-text-3)', fontSize: '2rem' }}>{icon}</div>}
      <p style={{ color: 'var(--c-text-2)', fontWeight: 500 }}>{title}</p>
      {description && <p className="text-sm max-w-xs" style={{ color: 'var(--c-text-3)' }}>{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
