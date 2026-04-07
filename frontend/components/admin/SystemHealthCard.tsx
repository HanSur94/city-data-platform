'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { SystemInfo } from '@/types/admin'

interface SystemHealthCardProps {
  systemInfo: SystemInfo
  checkedAt: string
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const parts: string[] = []
  if (d > 0) parts.push(`${d}d`)
  if (h > 0) parts.push(`${h}h`)
  parts.push(`${m}m`)
  return parts.join(' ')
}

export function SystemHealthCard({ systemInfo, checkedAt }: SystemHealthCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Systemgesundheit</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-muted-foreground mb-1">DB-Status</p>
            <div className="flex items-center gap-2">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  systemInfo.db_ok ? 'bg-emerald-500' : 'bg-red-500'
                }`}
              />
              <span className="text-sm font-medium">
                {systemInfo.db_ok ? 'Verbunden' : 'Fehler'}
              </span>
            </div>
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-1">TimescaleDB</p>
            <p className="text-sm font-medium">
              {systemInfo.timescaledb_version ?? '\u2014'}
            </p>
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-1">PostGIS</p>
            <p className="text-sm font-medium">
              {systemInfo.postgis_version ?? '\u2014'}
            </p>
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-1">Datenbankgroesse</p>
            <p className="text-sm font-medium">{systemInfo.total_db_size}</p>
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-1">Server-Uptime</p>
            <p className="text-sm font-medium">
              {formatUptime(systemInfo.server_uptime_seconds)}
            </p>
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-1">Letzter Check</p>
            <p className="text-sm font-medium">
              {new Date(checkedAt).toLocaleString('de-DE')}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
