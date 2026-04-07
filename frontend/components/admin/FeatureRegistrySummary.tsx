'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { FeatureDomainCount } from '@/types/admin'

interface FeatureRegistrySummaryProps {
  registry: FeatureDomainCount[]
}

export function FeatureRegistrySummary({ registry }: FeatureRegistrySummaryProps) {
  const totals = registry.reduce(
    (acc, r) => ({
      total_features: acc.total_features + r.total_features,
      with_semantic_id: acc.with_semantic_id + r.with_semantic_id,
      with_address: acc.with_address + r.with_address,
    }),
    { total_features: 0, with_semantic_id: 0, with_address: 0 },
  )

  function pct(part: number, whole: number): string {
    if (whole === 0) return '0%'
    return `${Math.round((part / whole) * 100)}%`
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Feature-Registry</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wide border-b">
                <th className="px-3 py-2">Domain</th>
                <th className="px-3 py-2 text-right">Gesamt</th>
                <th className="px-3 py-2 text-right">Mit Semantic-ID</th>
                <th className="px-3 py-2 text-right">Mit Adresse</th>
              </tr>
            </thead>
            <tbody>
              {registry.map((r) => (
                <tr key={r.domain} className="border-b border-muted/30">
                  <td className="px-3 py-2 capitalize">
                    {r.domain.replace(/_/g, ' ')}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {r.total_features.toLocaleString('de-DE')}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {r.with_semantic_id} / {r.total_features} ({pct(r.with_semantic_id, r.total_features)})
                  </td>
                  <td className="px-3 py-2 text-right">
                    {r.with_address.toLocaleString('de-DE')}
                  </td>
                </tr>
              ))}
              <tr className="font-bold border-t">
                <td className="px-3 py-2">Gesamt</td>
                <td className="px-3 py-2 text-right">
                  {totals.total_features.toLocaleString('de-DE')}
                </td>
                <td className="px-3 py-2 text-right">
                  {totals.with_semantic_id} / {totals.total_features} ({pct(totals.with_semantic_id, totals.total_features)})
                </td>
                <td className="px-3 py-2 text-right">
                  {totals.with_address.toLocaleString('de-DE')}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
