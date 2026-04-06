'use client';
import type { Feature } from 'geojson';

interface DemographicsPopupProps {
  feature: Feature;
}

/**
 * Popup for demographics data points.
 * Displays population, households, AGS, and data source.
 */
export default function DemographicsPopup({ feature }: DemographicsPopupProps) {
  const props = feature.properties ?? {};
  const population = props.population as number | undefined;
  const households = props.households as number | undefined;
  const ags = props.ags as string | undefined;
  const source = (props.data_source as string) ?? 'Zensus 2022';

  return (
    <div className="text-sm space-y-1 max-w-[220px]">
      <p className="text-[16px] font-semibold leading-tight">Demografie</p>
      {population != null && (
        <p className="text-[14px]">
          Einwohner: {population.toLocaleString('de-DE')}
        </p>
      )}
      {households != null && (
        <p className="text-[14px]">
          Haushalte: {households.toLocaleString('de-DE')}
        </p>
      )}
      {ags && (
        <p className="text-[13px] text-muted-foreground">AGS: {ags}</p>
      )}
      <p className="text-[12px] text-muted-foreground">Quelle: {source}</p>
    </div>
  );
}
