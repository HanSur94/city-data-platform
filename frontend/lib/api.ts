import type { LayerResponse } from '@/types/geojson';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchLayer(domain: string, town = 'aalen'): Promise<LayerResponse> {
  const res = await fetch(`${API_BASE}/api/layers/${domain}?town=${town}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
