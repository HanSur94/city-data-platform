'use client'

import type { HypertableStats } from '@/types/admin'

interface HypertableStatsTableProps {
  stats: HypertableStats[]
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatDate(iso: string | null): string {
  if (!iso) return '\u2014'
  const d = new Date(iso)
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function HypertableStatsTable({ stats }: HypertableStatsTableProps) {
  const sorted = [...stats].sort((a, b) => b.disk_size_bytes - a.disk_size_bytes)

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-background border-b">
          <tr className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <th className="px-4 py-3">Tabelle</th>
            <th className="px-4 py-3 text-right">Zeilen</th>
            <th className="px-4 py-3 text-right">Groesse</th>
            <th className="px-4 py-3 text-right">Chunks</th>
            <th className="px-4 py-3 text-right">Kompression</th>
            <th className="px-4 py-3">Zeitraum</th>
            <th className="px-4 py-3">Retention</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((ht, idx) => (
            <tr
              key={ht.table_name}
              className={idx % 2 === 0 ? 'bg-background' : 'bg-muted/20'}
            >
              <td className="px-4 py-3 font-mono text-xs">{ht.table_name}</td>
              <td className="px-4 py-3 text-right">
                {ht.row_count.toLocaleString('de-DE')}
              </td>
              <td className="px-4 py-3 text-right">{formatBytes(ht.disk_size_bytes)}</td>
              <td className="px-4 py-3 text-right">{ht.chunk_count}</td>
              <td className="px-4 py-3 text-right">
                {ht.compression_ratio !== null
                  ? `${ht.compression_ratio.toFixed(1)}x`
                  : '\u2014'}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {ht.oldest_timestamp || ht.newest_timestamp
                  ? `${formatDate(ht.oldest_timestamp)} \u2014 ${formatDate(ht.newest_timestamp)}`
                  : '\u2014'}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {ht.retention_policy ?? '\u2014'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
