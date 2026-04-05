'use client'
import { useSearchParams, useRouter } from 'next/navigation'
import { useCallback } from 'react'
import { subDays, endOfDay } from 'date-fns'

export interface UrlState {
  town: string
  layers: string[]
  zoom: number | null
  lat: number | null
  lng: number | null
  from: Date
  to: Date
  ts: Date | null // null = live (time slider at rightmost)
  domain: string | null // active detail panel
}

// NOTE: useUrlState uses useSearchParams internally.
// Any component that calls useUrlState MUST be rendered inside a <Suspense> boundary in the parent.
// This is enforced in Plan 07 (page.tsx integration).
export function useUrlState(defaultTown = 'aalen'): {
  state: UrlState
  update: (patch: Partial<Record<string, string | null>>) => void
} {
  const searchParams = useSearchParams()
  const router = useRouter()

  const state: UrlState = {
    town: searchParams.get('town') ?? defaultTown,
    layers: (searchParams.get('layers') ?? 'transit,aqi').split(',').filter(Boolean),
    zoom: searchParams.get('zoom') ? Number(searchParams.get('zoom')) : null,
    lat: searchParams.get('lat') ? Number(searchParams.get('lat')) : null,
    lng: searchParams.get('lng') ? Number(searchParams.get('lng')) : null,
    from: searchParams.get('from') ? new Date(searchParams.get('from')!) : subDays(new Date(), 1),
    to: searchParams.get('to') ? new Date(searchParams.get('to')!) : endOfDay(new Date()),
    ts: searchParams.get('ts') ? new Date(searchParams.get('ts')!) : null,
    domain: searchParams.get('domain') ?? null,
  }

  const update = useCallback(
    (patch: Partial<Record<string, string | null>>) => {
      const params = new URLSearchParams(searchParams.toString())
      for (const [k, v] of Object.entries(patch)) {
        if (v === null) params.delete(k)
        else params.set(k, v)
      }
      router.replace(`?${params.toString()}`, { scroll: false })
    },
    [searchParams, router],
  )

  return { state, update }
}
