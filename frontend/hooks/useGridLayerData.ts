'use client';
import { useState, useEffect } from 'react';
import { fetchGridLayer } from '@/lib/api';
import type { LayerResponse } from '@/types/geojson';

/**
 * Fetches grid layer data with a feature_type filter.
 * Polls every 60s for live data; stops polling when a historical timestamp is set.
 */
export function useGridLayerData(domain: string, featureType: string, town = 'aalen', timestamp?: Date | null) {
  const [data, setData] = useState<LayerResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const json = await fetchGridLayer(domain, featureType, town, timestamp);
        if (!cancelled) {
          setData(json);
          setError(false);
        }
      } catch {
        if (!cancelled) setError(true);
      }
    };
    load();
    if (timestamp) return () => { cancelled = true; };
    const id = setInterval(load, 60_000);
    return () => { cancelled = true; clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain, featureType, town, timestamp?.toISOString() ?? null]);

  return { data, error };
}
