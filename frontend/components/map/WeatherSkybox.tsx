'use client';

import { useEffect } from 'react';
import { useMap } from 'react-map-gl/maplibre';

interface WeatherSkyboxProps {
  condition: string | null;
}

/**
 * Fog presets keyed by weather category.
 *
 * MapLibre 5.x `map.setFog()` configures an atmospheric gradient visible at
 * the horizon. Each preset adjusts color, high-color (zenith), horizon blend
 * width, space color, and star intensity to match the current weather.
 */
type FogPreset = {
  color: string;
  'high-color': string;
  'horizon-blend': number;
  'space-color': string;
  'star-intensity': number;
};

const FOG_PRESETS: Record<string, FogPreset> = {
  clear: {
    color: '#ddeeff',
    'high-color': '#245bde',
    'horizon-blend': 0.08,
    'space-color': '#1a1a2e',
    'star-intensity': 0.0,
  },
  overcast: {
    color: '#c8c8c8',
    'high-color': '#8a8a8a',
    'horizon-blend': 0.15,
    'space-color': '#4a4a4a',
    'star-intensity': 0.0,
  },
  rain: {
    color: '#9a9a9a',
    'high-color': '#5a5a5a',
    'horizon-blend': 0.2,
    'space-color': '#2a2a2a',
    'star-intensity': 0.0,
  },
  night: {
    color: '#1a1a3e',
    'high-color': '#0a0a2e',
    'horizon-blend': 0.1,
    'space-color': '#000011',
    'star-intensity': 0.6,
  },
};

/**
 * Map Bright Sky API icon values to fog preset keys.
 * Unknown / null conditions default to "clear".
 */
function conditionToPreset(condition: string | null): string {
  if (!condition) return 'clear';

  switch (condition) {
    case 'clear-night':
    case 'partly-cloudy-night':
      return 'night';
    case 'cloudy':
    case 'fog':
      return 'overcast';
    case 'rain':
    case 'sleet':
    case 'snow':
      return 'rain';
    case 'clear-day':
    case 'partly-cloudy-day':
    case 'wind':
    default:
      return 'clear';
  }
}

/**
 * WeatherSkybox — sets MapLibre fog/atmosphere based on current weather.
 *
 * Renders nothing to the DOM. Uses the `useMap()` hook from react-map-gl to
 * get the underlying MapLibre instance and calls `map.setFog()` when the
 * weather condition changes.
 */
export default function WeatherSkybox({ condition }: WeatherSkyboxProps) {
  const { current: mapRef } = useMap();

  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;

    const preset = FOG_PRESETS[conditionToPreset(condition)];

    // Apply fog when the map style is loaded
    const apply = () => {
      try {
        (map as any).setFog(preset);
      } catch {
        // setFog may not be available in all MapLibre versions — silently skip
      }
    };

    if (map.isStyleLoaded()) {
      apply();
    } else {
      map.once('style.load', apply);
    }
  }, [condition, mapRef]);

  return null;
}
