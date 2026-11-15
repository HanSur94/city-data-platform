import type { Map as MapLibreMap } from 'maplibre-gl';

/**
 * Run `apply` now (if the style is ready) and again after every `style.load`.
 *
 * react-map-gl swaps base styles with a style diff, which resets imperatively
 * applied state (sky, light, terrain, layer visibility) to whatever the new style
 * says, and MapLibre 6.18 fires 'style.load' after both diffs and full reloads.
 * `map.isStyleLoaded()` must not be used as the readiness check here because it
 * stays false while any source tiles are still loading; `map.style._loaded` is the
 * flag react-map-gl itself uses.
 *
 * Returns a function that unsubscribes the listener.
 */
export function applyOnStyleLoad(map: MapLibreMap, apply: () => void): () => void {
  if (map.style?._loaded) {
    apply();
  }
  map.on('style.load', apply);
  return () => {
    map.off('style.load', apply);
  };
}
