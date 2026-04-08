'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';
import { lineColor } from '@/components/map/BusPositionLayer';

interface BusStopPopupProps {
  feature: Feature;
}

export default function BusStopPopup({ feature }: BusStopPopupProps) {
  const props = feature.properties ?? {};
  const stopName = (props.stop_name as string) ?? 'Haltestelle';
  const routeNamesRaw = (props.route_names as string) ?? '';
  const routeNames = routeNamesRaw
    ? routeNamesRaw.split(',').map((r) => r.trim()).filter(Boolean)
    : [];

  return (
    <div className="text-sm space-y-1 max-w-[220px]">
      <p className="text-[16px] font-semibold leading-tight">
        {stopName}
      </p>
      <p className="text-[12px] text-muted-foreground">
        Haltestelle
      </p>
      {routeNames.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {routeNames.map((name) => (
            <span
              key={name}
              style={{ backgroundColor: lineColor(name) }}
              className="inline-block rounded-full px-2 py-0.5 text-[11px] font-medium text-white leading-none"
            >
              {name}
            </span>
          ))}
        </div>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['transit'].sourceName}
        sourceUrl={LAYER_METADATA['transit'].sourceUrl}
        dataType="STATIC"
        timestamp={null}
      />
    </div>
  );
}
