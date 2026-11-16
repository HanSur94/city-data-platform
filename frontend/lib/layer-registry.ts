/**
 * Single registry of every switchable map layer.
 *
 * One entry per layer: internal key, URL key (the `layers` query parameter),
 * German label, sidebar group and, where applicable, the key under which the
 * backend reports its metadata / status. Page state, URL writes and the
 * sidebar are all derived from this list.
 */

export type LayerGroupId =
  | 'environment'
  | 'transport'
  | 'energy'
  | 'community'
  | 'infrastructure'
  | 'mapOverlays'
  | 'threeD'

export interface LayerGroupDef {
  id: LayerGroupId
  title: string
  /** Data groups are covered by the master switch; map overlays and 3D are not. */
  isDataGroup: boolean
}

export const LAYER_GROUPS: readonly LayerGroupDef[] = [
  { id: 'environment', title: 'Umwelt', isDataGroup: true },
  { id: 'transport', title: 'Verkehr', isDataGroup: true },
  { id: 'energy', title: 'Energie', isDataGroup: true },
  { id: 'community', title: 'Gemeinwesen', isDataGroup: true },
  { id: 'infrastructure', title: 'Infrastruktur', isDataGroup: true },
  { id: 'mapOverlays', title: 'Karte & Overlays', isDataGroup: false },
  { id: 'threeD', title: '3D', isDataGroup: false },
]

interface LayerEntryShape {
  key: string
  urlKey: string
  label: string
  group: LayerGroupId
  /** Key of the layer in the backend metadata response, when it has one. */
  metadataKey?: string
  /** Drawn straight from an external WMS: connector status does not describe it. */
  externalWms?: boolean
}

const REGISTRY = [
  { key: 'airQuality', urlKey: 'aqi', label: 'Luftqualitaet', group: 'environment', metadataKey: 'airQuality' },
  { key: 'water', urlKey: 'water', label: 'Pegel & Gewaesser', group: 'environment', metadataKey: 'water' },
  { key: 'kocher', urlKey: 'kocher', label: 'Kocher Pegel (LHP)', group: 'environment', metadataKey: 'kocher' },
  { key: 'floodHazard', urlKey: 'flood', label: 'Hochwassergefahr (HQ100)', group: 'environment', externalWms: true },
  { key: 'railNoise', urlKey: 'rail_noise', label: 'Bahnlaerm (Lden)', group: 'environment', externalWms: true },
  { key: 'lubwEnv', urlKey: 'lubw_env', label: 'Schutzgebiete (LUBW)', group: 'environment' },
  { key: 'roadNoise', urlKey: 'road_noise', label: 'Strassenlaerm (LUBW)', group: 'environment', metadataKey: 'roadNoise', externalWms: true },
  { key: 'transit', urlKey: 'transit', label: 'OEPNV (Bus & Bahn)', group: 'transport', metadataKey: 'transit' },
  { key: 'busPosition', urlKey: 'bus_position', label: 'Bus-Positionen (live)', group: 'transport', metadataKey: 'busPosition' },
  { key: 'traffic', urlKey: 'traffic', label: 'Verkehrszaehlstellen (BASt)', group: 'transport', metadataKey: 'traffic' },
  { key: 'trafficFlow', urlKey: 'traffic_flow', label: 'Verkehrsfluss (TomTom)', group: 'transport', metadataKey: 'trafficFlow' },
  { key: 'autobahn', urlKey: 'autobahn', label: 'Autobahn-Stoerungen (A7/A6)', group: 'transport', metadataKey: 'autobahn' },
  { key: 'cycling', urlKey: 'cycling', label: 'Radinfrastruktur (OSM)', group: 'transport', metadataKey: 'cycling' },
  { key: 'energy', urlKey: 'energy', label: 'Erneuerbare Anlagen (MaStR)', group: 'energy', metadataKey: 'energy' },
  { key: 'solarGlow', urlKey: 'solar_glow', label: 'Solar-Erzeugung (live)', group: 'energy', metadataKey: 'solarGlow' },
  { key: 'fernwaerme', urlKey: 'fernwaerme', label: 'Fernwaerme-Netz', group: 'energy', metadataKey: 'fernwaerme' },
  { key: 'heatDemand', urlKey: 'heat_demand', label: 'Waermebedarf (KEA-BW)', group: 'energy', metadataKey: 'heatDemand' },
  { key: 'schools', urlKey: 'schools', label: 'Schulen & Kitas', group: 'community', metadataKey: 'schools' },
  { key: 'healthcare', urlKey: 'healthcare', label: 'Gesundheit', group: 'community', metadataKey: 'healthcare' },
  { key: 'parks', urlKey: 'parks', label: 'Parks & Spielplaetze', group: 'community', metadataKey: 'parks' },
  { key: 'waste', urlKey: 'waste', label: 'Wertstoffhoefe', group: 'community', metadataKey: 'waste' },
  { key: 'police', urlKey: 'police', label: 'Polizeimeldungen', group: 'community' },
  { key: 'demographics', urlKey: 'demographics', label: 'Demografie (Zensus)', group: 'community', metadataKey: 'demographics', externalWms: true },
  { key: 'roadworks', urlKey: 'roadworks', label: 'Baustellen (OSM)', group: 'infrastructure', metadataKey: 'roadworks' },
  { key: 'evCharging', urlKey: 'ev_charging', label: 'E-Ladesaeulen (live)', group: 'infrastructure', metadataKey: 'evCharging' },
  { key: 'solarPotential', urlKey: 'solar_potential', label: 'Solarpotenzial Daecher', group: 'infrastructure', metadataKey: 'solarPotential', externalWms: true },
  { key: 'parking', urlKey: 'parking', label: 'Parkhaeuser', group: 'infrastructure', metadataKey: 'parking' },
  { key: 'cadastral', urlKey: 'cadastral', label: 'Kataster (ALKIS)', group: 'mapOverlays', externalWms: true },
  { key: 'hillshade', urlKey: 'hillshade', label: 'Gelaenderelief (DGM)', group: 'mapOverlays' },
  { key: 'buildings3d', urlKey: 'buildings3d', label: '3D-Gebaeude', group: 'threeD' },
  { key: 'terrain3d', urlKey: 'terrain3d', label: '3D-Gelaende', group: 'threeD' },
] as const satisfies readonly LayerEntryShape[]

export type LayerKey = (typeof REGISTRY)[number]['key']

export interface LayerEntry {
  key: LayerKey
  urlKey: string
  label: string
  group: LayerGroupId
  metadataKey?: string
  externalWms?: boolean
}

/** Widened view of the registry (optional fields are accessible on every entry). */
export const LAYERS: readonly LayerEntry[] = REGISTRY

export const LAYER_BY_KEY = Object.fromEntries(
  LAYERS.map((layer) => [layer.key, layer]),
) as Record<LayerKey, LayerEntry>

export const ALL_LAYER_KEYS: readonly LayerKey[] = LAYERS.map((layer) => layer.key)

const DATA_GROUP_IDS = new Set<LayerGroupId>(
  LAYER_GROUPS.filter((group) => group.isDataGroup).map((group) => group.id),
)

/** Layers of the data groups: what the master switch controls. */
export const DATA_LAYER_KEYS: readonly LayerKey[] = LAYERS.filter((layer) =>
  DATA_GROUP_IDS.has(layer.group),
).map((layer) => layer.key)

export function layerKeysInGroup(group: LayerGroupId): LayerKey[] {
  return LAYERS.filter((layer) => layer.group === group).map((layer) => layer.key)
}

export type LayerVisibility = Record<LayerKey, boolean>

const LAYER_BY_URL_KEY = new Map<string, LayerEntry>(
  LAYERS.map((layer) => [layer.urlKey, layer]),
)

/** Visibility of every layer from the URL's layer list. Unknown url keys are ignored. */
export function visibilityFromUrl(urlKeys: readonly string[]): LayerVisibility {
  const active = new Set(urlKeys)
  return Object.fromEntries(
    LAYERS.map((layer) => [layer.key, active.has(layer.urlKey)]),
  ) as LayerVisibility
}

/**
 * Next URL layer list after switching `keys` on or off.
 *
 * Keeps the registry url keys of `current` in their current order,
 * de-duplicated; unknown keys are dropped. Switching on appends the missing url
 * keys of `keys` in registry order; switching off removes them.
 */
export function nextUrlLayers(
  current: readonly string[],
  keys: readonly LayerKey[],
  on: boolean,
): string[] {
  const seen = new Set<string>()
  const kept: string[] = []
  for (const urlKey of current) {
    if (LAYER_BY_URL_KEY.has(urlKey) && !seen.has(urlKey)) {
      seen.add(urlKey)
      kept.push(urlKey)
    }
  }

  const targets = new Set(keys.map((key) => LAYER_BY_KEY[key].urlKey))
  if (!on) return kept.filter((urlKey) => !targets.has(urlKey))

  const result = [...kept]
  for (const layer of LAYERS) {
    if (targets.has(layer.urlKey) && !seen.has(layer.urlKey)) {
      result.push(layer.urlKey)
    }
  }
  return result
}

export type GroupSwitchState = 'on' | 'off' | 'mixed'

export function countActive(keys: readonly LayerKey[], visibility: LayerVisibility): number {
  return keys.filter((key) => visibility[key]).length
}

export function groupSwitchState(
  keys: readonly LayerKey[],
  visibility: LayerVisibility,
): GroupSwitchState {
  const active = countActive(keys, visibility)
  if (active === 0) return 'off'
  if (active === keys.length) return 'on'
  return 'mixed'
}
