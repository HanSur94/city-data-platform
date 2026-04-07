'use client'
import { useState, useEffect, useRef } from 'react'
import { fetchKpi } from '@/lib/api'
import type { KPIResponse } from '@/types/kpi'

export function useKpi(town = 'aalen') {
  const [data, setData] = useState<KPIResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(false)
  const [lastFetched, setLastFetched] = useState<Date | null>(null)
  const hasLoaded = useRef(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      if (hasLoaded.current) setRefreshing(true)
      try {
        const json = await fetchKpi(town)
        if (!cancelled) {
          setData(json)
          setLoading(false)
          setRefreshing(false)
          setError(false)
          setLastFetched(new Date())
          hasLoaded.current = true
        }
      } catch {
        if (!cancelled) { setLoading(false); setRefreshing(false); setError(true) }
      }
    }
    load()
    const id = setInterval(load, 60_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [town])

  return { data, loading, refreshing, error, lastFetched }
}
