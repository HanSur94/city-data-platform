'use client'
import { Card, CardContent } from '@/components/ui/card'
import { TrendArrow } from './TrendArrow'

interface KpiTileProps {
  domain: string         // 'aqi' | 'weather' | 'transit'
  label: string          // "Luftqualität" | "Wetter" | "ÖPNV"
  icon: React.ReactNode
  value: string | null   // Display-size primary metric, null if no data
  unit: string           // "AQI" | "°C" | "Linien"
  trend: number | null   // % change vs yesterday; null = no trend (transit)
  active: boolean        // is this tile's domain the activeDomain?
  onSelect: (domain: string) => void
}

export function KpiTile({ domain, label, icon, value, unit, trend, active, onSelect }: KpiTileProps) {
  return (
    <Card
      role="button"
      tabIndex={0}
      className={`min-h-[80px] cursor-pointer select-none transition-colors hover:bg-secondary p-4 ${
        active ? 'ring-2 ring-primary' : ''
      }`}
      onClick={() => onSelect(domain)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelect(domain) }}
    >
      <CardContent className="p-0 flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">{icon}</span>
          <span className="text-[16px] font-semibold">{label}</span>
        </div>
        {value !== null ? (
          <>
            <span className="text-[28px] font-semibold leading-none">{value}</span>
            <span className="text-[12px] text-muted-foreground">{unit}</span>
            <TrendArrow percent={trend} />
          </>
        ) : (
          <span className="text-[14px] text-muted-foreground">Kein aktueller Messwert</span>
        )}
      </CardContent>
    </Card>
  )
}
