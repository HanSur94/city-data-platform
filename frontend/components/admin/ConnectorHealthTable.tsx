'use client'
import { StalenessBar } from './StalenessBar'
import type { AdminHealthItem } from '@/types/admin'

interface ConnectorHealthTableProps {
  connectors: AdminHealthItem[]
}

const STATUS_ORDER = { red: 0, yellow: 1, green: 2, never_fetched: 3 }

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return '—'
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 60) return 'gerade eben'
  if (diffSec < 3600) {
    const mins = Math.floor(diffSec / 60)
    return `vor ${mins} Min.`
  }
  if (diffSec < 86400) {
    const hours = Math.floor(diffSec / 3600)
    return `vor ${hours} Std.`
  }
  const days = Math.floor(diffSec / 86400)
  return `vor ${days} Tagen`
}

function formatInterval(seconds: number | null): string {
  if (seconds === null) return '—'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}min`
  return `${Math.round(seconds / 3600)}h`
}

export function ConnectorHealthTable({ connectors }: ConnectorHealthTableProps) {
  // Group by domain, sort within domain: red first, then yellow, then green
  const byDomain = connectors.reduce<Record<string, AdminHealthItem[]>>((acc, c) => {
    if (!acc[c.domain]) acc[c.domain] = []
    acc[c.domain].push(c)
    return acc
  }, {})

  // Sort domains by worst status
  const sortedDomains = Object.keys(byDomain).sort((a, b) => {
    const worstA = Math.min(...byDomain[a].map(c => STATUS_ORDER[c.status]))
    const worstB = Math.min(...byDomain[b].map(c => STATUS_ORDER[c.status]))
    return worstA - worstB
  })

  // Sort connectors within each domain
  for (const domain of sortedDomains) {
    byDomain[domain].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status])
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-background border-b">
          <tr className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <th className="px-4 py-3">Domain</th>
            <th className="px-4 py-3">Konnektor</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Letzter Abruf</th>
            <th className="px-4 py-3 text-right">Fehler</th>
            <th className="px-4 py-3 text-right">Intervall</th>
          </tr>
        </thead>
        <tbody>
          {sortedDomains.map((domain) => (
            <>
              <tr key={`header-${domain}`} className="bg-muted/40">
                <td colSpan={6} className="px-4 py-2 font-semibold text-xs uppercase tracking-wider text-muted-foreground">
                  {domain.replace(/_/g, ' ')}
                </td>
              </tr>
              {byDomain[domain].map((connector, idx) => (
                <tr
                  key={connector.id}
                  className={idx % 2 === 0 ? 'bg-background' : 'bg-muted/20'}
                >
                  <td className="px-4 py-3 text-muted-foreground">—</td>
                  <td className="px-4 py-3 font-mono text-xs">{connector.connector_class}</td>
                  <td className="px-4 py-3">
                    <StalenessBar status={connector.status} />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatRelativeTime(connector.last_successful_fetch)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {connector.validation_error_count > 0 ? (
                      <span className="text-red-500 font-medium">{connector.validation_error_count}</span>
                    ) : (
                      <span className="text-muted-foreground">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    {formatInterval(connector.poll_interval)}
                  </td>
                </tr>
              ))}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}
