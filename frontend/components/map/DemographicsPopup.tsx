'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
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
      <DataSourceSection
        sourceName={LAYER_METADATA['demographics'].sourceName}
        sourceUrl={LAYER_METADATA['demographics'].sourceUrl}
        dataType={LAYER_METADATA['demographics'].dataType}
        timestamp={null}
      />
    </div>
  );
}
