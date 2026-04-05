'use client'
import { useState, useEffect } from 'react'
import { fetchTimeseries } from '@/lib/api'
import type { TimeseriesResponse } from '@/types/timeseries'

export function useTimeseries(domain: string, from: Date, to: Date, town = 'aalen') {
  const [data, setData] = useState<TimeseriesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        const json = await fetchTimeseries(domain, town, from, to)
        if (!cancelled) { setData(json); setLoading(false); setError(false) }
      } catch {
        if (!cancelled) { setLoading(false); setError(true) }
      }
    }
    load()
    return () => { cancelled = true }
    // Re-fetch when date range changes — use ISO strings as dep values to avoid object reference churn
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain, town, from.toISOString(), to.toISOString()])

  return { data, loading, error }
}
