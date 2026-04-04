import Badge from './Badge'
import Tooltip from './Tooltip'

type ConfidenceTier = 'reported' | 'estimated' | 'interpolated' | 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN' | string

const TIER_CONFIG: Record<string, { variant: 'green' | 'amber' | 'red' | 'gray'; label: string; description: string }> = {
  reported:    { variant: 'green', label: 'Reported',    description: 'Directly reported data from the source' },
  HIGH:        { variant: 'green', label: 'High',        description: 'High-confidence mapping to e-waste category' },
  estimated:   { variant: 'amber', label: 'Estimated',   description: 'Modelled or estimated — treat with caution' },
  MEDIUM:      { variant: 'amber', label: 'Medium',      description: 'Medium-confidence mapping; includes new goods' },
  interpolated:{ variant: 'amber', label: 'Interpolated',description: 'Gap-filled via linear interpolation' },
  LOW:         { variant: 'red',   label: 'Low',         description: 'Low-confidence mapping; mixed-use equipment' },
  UNKNOWN:     { variant: 'gray',  label: 'Unknown',     description: 'Confidence not determined' },
}

interface DataQualityBadgeProps {
  tier: ConfidenceTier | null | undefined
}

export default function DataQualityBadge({ tier }: DataQualityBadgeProps) {
  if (!tier) return null

  const config = TIER_CONFIG[tier] ?? { variant: 'gray' as const, label: tier, description: '' }

  return (
    <Tooltip content={config.description || tier} placement="top">
      <Badge variant={config.variant}>{config.label}</Badge>
    </Tooltip>
  )
}
