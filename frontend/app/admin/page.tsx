'use client'
import { useAdminMonitor } from '@/hooks/useAdminHealth'
import { SystemHealthCard } from '@/components/admin/SystemHealthCard'
import { HypertableStatsTable } from '@/components/admin/HypertableStatsTable'
import { FeatureRegistrySummary } from '@/components/admin/FeatureRegistrySummary'
import { StalenessBar } from '@/components/admin/StalenessBar'

function SkeletonTable() {
  return (
    <div className="space-y-2">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="h-12 rounded bg-muted animate-pulse" />
      ))}
    </div>
  )
}

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return '\u2014'
  const date = new Date(isoString)
  const now = new Date()
  const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000)

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
  if (seconds === null) return '\u2014'
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}min`
  return `${Math.round(seconds / 3600)}h`
}

export default function AdminPage() {
  const { data, loading, error } = useAdminMonitor('aalen')

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-2">Systemstatus</h1>
        {data && (
          <p className="text-sm text-muted-foreground mb-6">
            {data.town} &middot; Zuletzt gepr&uuml;ft:{' '}
            {new Date(data.checked_at).toLocaleString('de-DE')}
          </p>
        )}

        {loading && !data ? (
          <SkeletonTable />
        ) : error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-6">
            <p className="text-red-700 font-medium mb-3">
              Systemstatus konnte nicht geladen werden.
            </p>
            <button
              type="button"
              className="text-sm text-red-600 underline"
              onClick={() => window.location.reload()}
            >
              Seite neu laden
            </button>
          </div>
        ) : data ? (
          <div className="space-y-8">
            {/* System Health */}
            <SystemHealthCard
              systemInfo={data.system_info}
              checkedAt={data.checked_at}
            />

            {/* Hypertable Stats */}
            <section>
              <h2 className="text-lg font-semibold mb-3">Hypertables</h2>
              <HypertableStatsTable stats={data.hypertable_stats} />
            </section>

            {/* Connector Health */}
            <section>
              <h2 className="text-lg font-semibold mb-3">Konnektoren</h2>

              {/* Summary boxes */}
              <div className="flex gap-3 mb-4 flex-wrap">
                {(['green', 'yellow', 'red', 'never_fetched'] as const).map((status) => {
                  const count = data.connector_health.filter(
                    (c) => c.status === status,
                  ).length
                  const colorMap = {
                    green: 'bg-emerald-500',
                    yellow: 'bg-amber-500',
                    red: 'bg-red-500',
                    never_fetched: 'bg-slate-400',
                  }
                  const labelMap = {
                    green: 'OK',
                    yellow: 'Verzoegert',
                    red: 'Ausgefallen',
                    never_fetched: 'Nie abgerufen',
                  }
                  return (
                    <div
                      key={status}
                      className={`flex flex-col items-center rounded-lg px-6 py-4 text-white ${colorMap[status]}`}
                    >
                      <span className="text-3xl font-bold leading-none">
                        {count}
                      </span>
                      <span className="mt-1 text-sm font-medium">
                        {labelMap[status]}
                      </span>
                    </div>
                  )
                })}
              </div>

              {/* Connector table */}
              <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-background border-b">
                    <tr className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      <th className="px-4 py-3">Konnektor</th>
                      <th className="px-4 py-3">Domain</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Letzter Abruf</th>
                      <th className="px-4 py-3 text-right">Intervall</th>
                      <th className="px-4 py-3 text-right">Fehler</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.connector_health.map((c, idx) => (
                      <tr
                        key={`${c.connector_class}-${c.domain}`}
                        className={
                          idx % 2 === 0 ? 'bg-background' : 'bg-muted/20'
                        }
                      >
                        <td className="px-4 py-3 font-mono text-xs">
                          {c.connector_class}
                        </td>
                        <td className="px-4 py-3 capitalize">
                          {c.domain.replace(/_/g, ' ')}
                        </td>
                        <td className="px-4 py-3">
                          <StalenessBar status={c.status} />
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {formatRelativeTime(c.last_successful_fetch)}
                        </td>
                        <td className="px-4 py-3 text-right text-muted-foreground">
                          {formatInterval(c.poll_interval_seconds)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {c.validation_error_count > 0 ? (
                            <span className="text-red-500 font-medium">
                              {c.validation_error_count}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">0</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Feature Registry */}
            <section>
              <h2 className="text-lg font-semibold mb-3">Feature-Registry</h2>
              <FeatureRegistrySummary registry={data.feature_registry} />
            </section>
          </div>
        ) : null}
      </div>
    </div>
  )
}
