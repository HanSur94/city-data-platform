import { TrendingUp, TrendingDown } from 'lucide-react'

interface TrendArrowProps {
  percent: number | null  // null = no trend data
}

export function TrendArrow({ percent }: TrendArrowProps) {
  if (percent === null) return null
  if (Math.abs(percent) < 1) {
    return <span className="text-[12px] text-muted-foreground">Unverändert</span>
  }
  const up = percent > 0
  const Icon = up ? TrendingUp : TrendingDown
  const sign = up ? '+' : '−'
  return (
    <span className={`flex items-center gap-1 text-[12px] ${up ? 'text-red-500' : 'text-green-600'}`}>
      <Icon size={12} />
      {sign}{Math.abs(Math.round(percent))}% gegenüber gestern
    </span>
  )
}
