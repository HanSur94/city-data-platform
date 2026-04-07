'use client'
import { useState, useEffect } from 'react'
import { fetchAdminHealth, fetchAdminMonitor } from '@/lib/api'
import type { AdminHealthResponse, AdminMonitorResponse } from '@/types/admin'

export function useAdminHealth(town = 'aalen') {
  const [data, setData] = useState<AdminHealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const json = await fetchAdminHealth(town)
        if (!cancelled) { setData(json); setLoading(false); setError(false) }
      } catch {
        if (!cancelled) { setLoading(false); setError(true) }
      }
    }
    load()
    // Auto-refresh every 30 seconds for operator monitoring
    const id = setInterval(load, 30_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [town])

  return { data, loading, error }
}

export function useAdminMonitor(town = 'aalen') {
  const [data, setData] = useState<AdminMonitorResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const json = await fetchAdminMonitor(town)
        if (!cancelled) { setData(json); setLoading(false); setError(false) }
      } catch {
        if (!cancelled) { setLoading(false); setError(true) }
      }
    }
    load()
    const id = setInterval(load, 30_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [town])

  return { data, loading, error }
}
