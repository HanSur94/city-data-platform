'use client'
import { useAdminHealth } from '@/hooks/useAdminHealth'
import { ConnectorHealthTable } from '@/components/admin/ConnectorHealthTable'
import { StalenessBar } from '@/components/admin/StalenessBar'

function SummaryBox({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className={`flex flex-col items-center rounded-lg px-6 py-4 text-white ${color}`}>
      <span className="text-3xl font-bold leading-none">{count}</span>
      <span className="mt-1 text-sm font-medium">{label}</span>
    </div>
  )
}

function SkeletonTable() {
  return (
    <div className="space-y-2">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="h-12 rounded bg-muted animate-pulse" />
      ))}
    </div>
  )
}

export default function AdminPage() {
  const { data, loading, error } = useAdminHealth('aalen')

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-2">Systemstatus — Konnektoren</h1>
        {data && (
          <p className="text-sm text-muted-foreground mb-6">
            {data.town_display_name} · Zuletzt geprüft:{' '}
            {new Date(data.checked_at).toLocaleString('de-DE')}
          </p>
        )}

        {/* Summary bar */}
        {data && (
          <div className="flex gap-3 mb-8 flex-wrap">
            <SummaryBox
              label="OK"
              count={data.summary.green ?? 0}
              color="bg-emerald-500"
            />
            <SummaryBox
              label="Verzögert"
              count={data.summary.yellow ?? 0}
              color="bg-amber-500"
            />
            <SummaryBox
              label="Ausgefallen"
              count={data.summary.red ?? 0}
              color="bg-red-500"
            />
            <SummaryBox
              label="Nie abgerufen"
              count={data.summary.never_fetched ?? 0}
              color="bg-slate-400"
            />
          </div>
        )}

        {/* Legend */}
        <div className="flex gap-4 mb-6 text-sm text-muted-foreground flex-wrap">
          <div className="flex items-center gap-2"><StalenessBar status="green" /> Abruf innerhalb Intervall</div>
          <div className="flex items-center gap-2"><StalenessBar status="yellow" /> Überschreitung gelber Schwelle</div>
          <div className="flex items-center gap-2"><StalenessBar status="red" /> Überschreitung roter Schwelle</div>
        </div>

        {/* Content */}
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
          <ConnectorHealthTable connectors={data.connectors} />
        ) : null}
      </div>
    </div>
  )
}
