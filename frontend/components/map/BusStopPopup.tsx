'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface BusStopPopupProps {
  feature: Feature;
}

export default function BusStopPopup({ feature }: BusStopPopupProps) {
  const props = feature.properties ?? {};
  const stopName = (props.stop_name as string) ?? 'Haltestelle';

  return (
    <div className="text-sm space-y-1 max-w-[220px]">
      <p className="text-[16px] font-semibold leading-tight">
        {stopName}
      </p>
      <p className="text-[12px] text-muted-foreground">
        Haltestelle
      </p>
      <DataSourceSection
        sourceName={LAYER_METADATA['transit'].sourceName}
        sourceUrl={LAYER_METADATA['transit'].sourceUrl}
        dataType="STATIC"
        timestamp={null}
      />
    </div>
  );
}
