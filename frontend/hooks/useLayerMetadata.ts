'use client';

import { useState, useEffect, useCallback } from 'react';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import { fetchLayerMetadata } from '@/lib/api';

interface LayerMetaEntry {
  lastUpdated: string | null;
  isStale: boolean;
}

interface UseLayerMetadataResult {
  layerMeta: Record<string, LayerMetaEntry>;
  loading: boolean;
}

export function useLayerMetadata(town = 'aalen'): UseLayerMetadataResult {
  const [layerMeta, setLayerMeta] = useState<Record<string, LayerMetaEntry>>({});
  const [loading, setLoading] = useState(true);

  const fetchMeta = useCallback(async () => {
    try {
      const data = await fetchLayerMetadata(town);

      const now = Date.now();
      const result: Record<string, LayerMetaEntry> = {};

      for (const [key, entry] of Object.entries(data)) {
        const lastUpdated = entry.last_updated ?? null;
        let isStale = false;

        if (lastUpdated) {
          const staticMeta = LAYER_METADATA[key];
          if (staticMeta?.updateIntervalSeconds) {
            const elapsed = now - new Date(lastUpdated).getTime();
            isStale = elapsed > 2 * staticMeta.updateIntervalSeconds * 1000;
          }
        }

        result[key] = { lastUpdated, isStale };
      }

      setLayerMeta(result);
    } catch {
      // silently ignore fetch errors
    } finally {
      setLoading(false);
    }
  }, [town]);

  useEffect(() => {
    fetchMeta();
    const interval = setInterval(fetchMeta, 60_000);
    return () => clearInterval(interval);
  }, [fetchMeta]);

  return { layerMeta, loading };
}
