'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface RoadworksPopupProps {
  feature: Feature;
}

export default function RoadworksPopup({ feature }: RoadworksPopupProps) {
  const props = feature.properties ?? {};
  const name = props.name as string | undefined;
  const note = props.note as string | undefined;
  const description = props.description as string | undefined;

  return (
    <div className="text-sm space-y-1 max-w-[200px]">
      <p className="text-[16px] font-semibold leading-tight">
        {name ?? 'Baustelle'}
      </p>
      {(note ?? description) && (
        <p className="text-[13px]">{note ?? description}</p>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['roadworks'].sourceName}
        sourceUrl={LAYER_METADATA['roadworks'].sourceUrl}
        dataType={LAYER_METADATA['roadworks'].dataType}
        timestamp={(props.fetched_at as string) ?? null}
      />
    </div>
  );
}
