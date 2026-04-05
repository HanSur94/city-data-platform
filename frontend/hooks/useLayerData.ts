'use client';
import { useState, useEffect } from 'react';
import { fetchLayer } from '@/lib/api';
import type { LayerResponse } from '@/types/geojson';

export function useLayerData(domain: string, town = 'aalen', timestamp?: Date | null) {
  const [data, setData] = useState<LayerResponse | null>(null);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const json = await fetchLayer(domain, town, timestamp);
        if (!cancelled) {
          setData(json);
          setLastFetched(new Date());
          setError(false);
        }
      } catch {
        if (!cancelled) setError(true);
      }
    };
    load();
    // Historical data (timestamp set) does not auto-refresh — stop polling
    if (timestamp) return () => { cancelled = true; };
    const id = setInterval(load, 60_000);
    return () => { cancelled = true; clearInterval(id); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain, town, timestamp?.toISOString() ?? null]);

  return { data, lastFetched, error };
}
