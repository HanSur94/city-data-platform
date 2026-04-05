'use client'
import { useState, useEffect } from 'react'
import { fetchKpi } from '@/lib/api'
import type { KPIResponse } from '@/types/kpi'

export function useKpi(town = 'aalen') {
  const [data, setData] = useState<KPIResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const json = await fetchKpi(town)
        if (!cancelled) { setData(json); setLoading(false); setError(false) }
      } catch {
        if (!cancelled) { setLoading(false); setError(true) }
      }
    }
    load()
    const id = setInterval(load, 60_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [town])

  return { data, loading, error }
}
