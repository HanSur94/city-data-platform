'use client';
import { useEffect, useState } from 'react';

export interface FeatureData {
  feature_id: string;
  semantic_id: string | null;
  domain: string;
  properties: Record<string, unknown>;
  observations: Record<string, { timestamp: string; values: Record<string, unknown> }>;
}

interface UseFeatureDataResult {
  data: FeatureData | null;
  loading: boolean;
  error: string | null;
}

export function useFeatureData(featureId: string | null): UseFeatureDataResult {
  const [data, setData] = useState<FeatureData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!featureId) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    fetch(`/api/features/${encodeURIComponent(featureId)}/data`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Fehler beim Laden der Gebaeudetdaten (${res.status})`);
        }
        return res.json() as Promise<FeatureData>;
      })
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [featureId]);

  return { data, loading, error };
}
