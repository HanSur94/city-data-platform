/**
 * Approximate solar position (NOAA fractional-year formulas).
 * Azimuth is degrees clockwise from north in [0, 360); altitude is degrees above
 * the horizon in [-90, 90]. Accurate to well under a degree, plenty for lighting.
 */
export function sunPosition(
  date: Date,
  lat: number,
  lng: number,
): { azimuthDeg: number; altitudeDeg: number } {
  const rad = Math.PI / 180;

  const startOfYear = Date.UTC(date.getUTCFullYear(), 0, 1);
  const dayOfYear = Math.floor((date.getTime() - startOfYear) / 86400000) + 1;
  const utcHours = date.getUTCHours() + date.getUTCMinutes() / 60 + date.getUTCSeconds() / 3600;
  const gamma = ((2 * Math.PI) / 365) * (dayOfYear - 1 + (utcHours - 12) / 24);

  // Equation of time (minutes)
  const eqTime =
    229.18 *
    (0.000075 +
      0.001868 * Math.cos(gamma) -
      0.032077 * Math.sin(gamma) -
      0.014615 * Math.cos(2 * gamma) -
      0.040849 * Math.sin(2 * gamma));

  // Solar declination (radians)
  const decl =
    0.006918 -
    0.399912 * Math.cos(gamma) +
    0.070257 * Math.sin(gamma) -
    0.006758 * Math.cos(2 * gamma) +
    0.000907 * Math.sin(2 * gamma) -
    0.002697 * Math.cos(3 * gamma) +
    0.00148 * Math.sin(3 * gamma);

  const trueSolarTimeMin = utcHours * 60 + eqTime + 4 * lng;
  const hourAngle = (trueSolarTimeMin / 4 - 180) * rad;
  const latRad = lat * rad;

  const sinAlt =
    Math.sin(latRad) * Math.sin(decl) + Math.cos(latRad) * Math.cos(decl) * Math.cos(hourAngle);
  const altitude = Math.asin(Math.min(1, Math.max(-1, sinAlt)));

  const azimuth =
    Math.atan2(
      Math.sin(hourAngle),
      Math.cos(hourAngle) * Math.sin(latRad) - Math.tan(decl) * Math.cos(latRad),
    ) /
      rad +
    180;

  return {
    azimuthDeg: ((azimuth % 360) + 360) % 360,
    altitudeDeg: altitude / rad,
  };
}
