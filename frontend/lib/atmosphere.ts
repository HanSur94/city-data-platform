import type { LightSpecification, SkySpecification } from 'maplibre-gl';

export type WeatherCategory = 'clear' | 'overcast' | 'precip';

/** Collapse a Bright Sky icon string into a coarse category. Unknown/null -> 'clear'. */
export function weatherCategory(condition: string | null | undefined): WeatherCategory {
  switch (condition) {
    case 'cloudy':
    case 'fog':
      return 'overcast';
    case 'rain':
    case 'sleet':
    case 'snow':
    case 'hail':
    case 'thunderstorm':
      return 'precip';
    default:
      return 'clear';
  }
}

// Sun bands (altitude in degrees): night < -6, twilight -6..6, low sun 6..20, day > 20.
const NIGHT_MAX = -6;
const TWILIGHT_MAX = 6;
const LOW_SUN_MAX = 20;

const DAY_SKY: Record<WeatherCategory, SkySpecification> = {
  clear: {
    'sky-color': '#5a8fd8',
    'horizon-color': '#cfe3f5',
    'fog-color': '#dfe9f3',
    'sky-horizon-blend': 0.5,
    'horizon-fog-blend': 0.6,
    'fog-ground-blend': 0.5,
  },
  overcast: {
    'sky-color': '#9aa3ad',
    'horizon-color': '#c9ced3',
    'fog-color': '#cfd3d7',
    'sky-horizon-blend': 0.7,
    'horizon-fog-blend': 0.8,
    'fog-ground-blend': 0.6,
  },
  precip: {
    'sky-color': '#5f656d',
    'horizon-color': '#8a9097',
    'fog-color': '#8f949a',
    'sky-horizon-blend': 0.8,
    'horizon-fog-blend': 0.9,
    'fog-ground-blend': 0.7,
  },
};

const TWILIGHT_SKY: Record<WeatherCategory, SkySpecification> = {
  clear: {
    'sky-color': '#3a5a8c',
    'horizon-color': '#f2a65a',
    'fog-color': '#e8b98a',
    'sky-horizon-blend': 0.6,
    'horizon-fog-blend': 0.7,
    'fog-ground-blend': 0.5,
  },
  overcast: {
    'sky-color': '#6f747c',
    'horizon-color': '#f2a65a',
    'fog-color': '#e8b98a',
    'sky-horizon-blend': 0.7,
    'horizon-fog-blend': 0.8,
    'fog-ground-blend': 0.6,
  },
  precip: {
    'sky-color': '#6f747c',
    'horizon-color': '#d9965a',
    'fog-color': '#c9a584',
    'sky-horizon-blend': 0.8,
    'horizon-fog-blend': 0.9,
    'fog-ground-blend': 0.7,
  },
};

const NIGHT_SKY: SkySpecification = {
  'sky-color': '#0b1026',
  'horizon-color': '#1c2540',
  'fog-color': '#0e1424',
  'sky-horizon-blend': 0.5,
  'horizon-fog-blend': 0.6,
  'fog-ground-blend': 0.5,
};

/** Sky colours for the current weather and sun altitude (degrees). */
/**
 * Sky presets for the dark basemap. A realistic bright sky above a near-black
 * ground reads as a rendering error, so the dark style keeps a deep-blue sky and
 * only varies its tint with weather and sun height.
 */
const DARK_DAY_SKY: Record<WeatherCategory, SkySpecification> = {
  clear: {
    'sky-color': '#0d1b33',
    'horizon-color': '#2f5184',
    'fog-color': '#1a2b45',
    'sky-horizon-blend': 0.6,
    'horizon-fog-blend': 0.7,
    'fog-ground-blend': 0.4,
  },
  overcast: {
    'sky-color': '#161b24',
    'horizon-color': '#3a4352',
    'fog-color': '#222a36',
    'sky-horizon-blend': 0.7,
    'horizon-fog-blend': 0.8,
    'fog-ground-blend': 0.5,
  },
  precip: {
    'sky-color': '#0f1319',
    'horizon-color': '#2a313c',
    'fog-color': '#1a2029',
    'sky-horizon-blend': 0.8,
    'horizon-fog-blend': 0.9,
    'fog-ground-blend': 0.6,
  },
};

const DARK_TWILIGHT_SKY: SkySpecification = {
  'sky-color': '#141a33',
  'horizon-color': '#b3683a',
  'fog-color': '#3a2c33',
  'sky-horizon-blend': 0.6,
  'horizon-fog-blend': 0.7,
  'fog-ground-blend': 0.4,
};

/**
 * @param darkBase true when the dark basemap is active (see DARK_DAY_SKY).
 */
export function skyFor(
  condition: string | null | undefined,
  altitudeDeg: number,
  darkBase = false,
): SkySpecification {
  if (altitudeDeg < NIGHT_MAX) return { ...NIGHT_SKY };
  const category = weatherCategory(condition);
  if (altitudeDeg <= TWILIGHT_MAX) {
    return darkBase ? { ...DARK_TWILIGHT_SKY } : { ...TWILIGHT_SKY[category] };
  }
  return darkBase ? { ...DARK_DAY_SKY[category] } : { ...DAY_SKY[category] };
}

/**
 * Directional light following the sun. The polar angle is clamped so buildings
 * never go fully black at night or flat at noon.
 */
export function lightFor(azimuthDeg: number, altitudeDeg: number): LightSpecification {
  const azimuth = ((azimuthDeg % 360) + 360) % 360;
  const polar = Math.min(80, Math.max(15, 90 - altitudeDeg));

  let color: string;
  let intensity: number;
  if (altitudeDeg < NIGHT_MAX) {
    color = '#8fa3d6';
    intensity = 0.25;
  } else if (altitudeDeg <= TWILIGHT_MAX) {
    color = '#ffb37a';
    intensity = 0.4;
  } else if (altitudeDeg <= LOW_SUN_MAX) {
    color = '#ffd2a1';
    intensity = 0.5;
  } else {
    color = '#ffffff';
    intensity = 0.55;
  }

  return { anchor: 'map', position: [1.5, azimuth, polar], color, intensity };
}
