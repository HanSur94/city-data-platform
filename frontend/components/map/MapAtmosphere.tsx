'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMap } from 'react-map-gl/maplibre';
import { sunPosition } from '@/lib/sun';
import { lightFor, skyFor } from '@/lib/atmosphere';
import { applyOnStyleLoad } from './applyOnStyleLoad';

interface MapAtmosphereProps {
  /** Bright Sky weather icon, or null when unknown. */
  condition: string | null;
  /** Time-slider timestamp; null = live (current time). */
  timestamp: Date | null;
  center: { lat: number; lng: number };
}

const REFRESH_MS = 5 * 60 * 1000;

/**
 * Draws a sky above the horizon and lights the 3D scene from the sun position for
 * the current time (or the time-slider timestamp) and the current weather.
 * Renders nothing to the DOM.
 */
export default function MapAtmosphere({ condition, timestamp, center }: MapAtmosphereProps) {
  const { current: mapRef } = useMap();
  const [now, setNow] = useState(() => new Date());

  // Live clock: only ticks while no historical timestamp is selected.
  useEffect(() => {
    if (timestamp) return;
    const refresh = () => setNow(new Date());
    const initial = setTimeout(refresh, 0);
    const interval = setInterval(refresh, REFRESH_MS);
    return () => {
      clearTimeout(initial);
      clearInterval(interval);
    };
  }, [timestamp]);

  const time = timestamp ?? now;
  const sun = useMemo(
    () => sunPosition(time, center.lat, center.lng),
    [time, center.lat, center.lng],
  );
  const sky = useMemo(() => skyFor(condition, sun.altitudeDeg), [condition, sun.altitudeDeg]);
  const light = useMemo(
    () => lightFor(sun.azimuthDeg, sun.altitudeDeg),
    [sun.azimuthDeg, sun.altitudeDeg],
  );

  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    return applyOnStyleLoad(map, () => {
      map.setSky(sky);
      map.setLight(light);
    });
  }, [mapRef, sky, light]);

  return null;
}
