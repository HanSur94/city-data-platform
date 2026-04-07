'use client'
import { Card, CardContent } from '@/components/ui/card'
import { TrendArrow } from './TrendArrow'
import { DataTypeBadge } from '@/components/ui/DataTypeBadge'
import { Loader2 } from 'lucide-react'
import type { DataType } from '@/lib/layer-metadata'

interface KpiTileProps {
  domain: string         // 'aqi' | 'weather' | 'transit'
  label: string          // "Luftqualität" | "Wetter" | "ÖPNV"
  icon: React.ReactNode
  value: string | null   // Display-size primary metric, null if no data
  unit: string           // "AQI" | "°C" | "Linien"
  trend: number | null   // % change vs yesterday; null = no trend (transit)
  active?: boolean       // deprecated — kept for backward compat, no longer styled
  onSelect: (domain: string) => void
  children?: React.ReactNode  // optional slot for compact sub-charts (e.g. EnergyMixBar)
  sourceAbbrev?: string
  sourceTimestamp?: string
  dataType?: DataType
  refreshing?: boolean
}

export function KpiTile({ domain, label, icon, value, unit, trend, onSelect, children, sourceAbbrev, sourceTimestamp, dataType, refreshing }: KpiTileProps) {
  return (
    <Card
      role="button"
      tabIndex={0}
      className="min-h-[80px] cursor-pointer select-none transition-colors hover:bg-secondary p-4"
      onClick={() => onSelect(domain)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelect(domain) }}
    >
      <CardContent className="p-0 flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">{icon}</span>
          <span className="text-[16px] font-semibold">{label}</span>
          {refreshing && (
            <Loader2 className="h-3.5 w-3.5 text-muted-foreground animate-spin ml-auto" />
          )}
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
        {children && <div className="mt-1">{children}</div>}
        {sourceAbbrev && (
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-1">
            <span>{sourceAbbrev}</span>
            <span>&middot;</span>
            <span>{sourceTimestamp ?? '--:--'}</span>
            {dataType && (
              <>
                <span>&middot;</span>
                <DataTypeBadge dataType={dataType} size="sm" />
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
