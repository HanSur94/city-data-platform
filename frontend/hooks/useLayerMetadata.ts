'use client';

import { useState, useEffect, useCallback } from 'react';
import { fetchLayerMetadata, isLayerStatus } from '@/lib/api';
import type { LayerStatus } from '@/lib/api';

export type LayerMetaEntry = {
  lastUpdated: string | null;
  /** undefined when the backend sent no (or an unknown) status. */
  status: LayerStatus | undefined;
  isStale: boolean;
};

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
      const result: Record<string, LayerMetaEntry> = {};

      if (Array.isArray(data?.layers)) {
        for (const item of data.layers) {
          if (typeof item?.layer_key !== 'string') continue;
          // An older backend without the field must never produce a false "Keine Daten".
          const status = isLayerStatus(item.status) ? item.status : undefined;
          result[item.layer_key] = {
            lastUpdated: item.last_updated ?? null,
            status,
            isStale: status === 'stale',
          };
        }
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
