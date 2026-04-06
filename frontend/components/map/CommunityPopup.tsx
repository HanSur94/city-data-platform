'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface CommunityPopupProps {
  feature: Feature;
}

const CATEGORY_LABELS: Record<string, string> = {
  school: 'Schule/Kita',
  healthcare: 'Gesundheit',
  park: 'Park/Spielplatz',
  waste: 'Wertstoffhof',
};

export default function CommunityPopup({ feature }: CommunityPopupProps) {
  const props = feature.properties ?? {};
  const name = props.name as string | undefined;
  const address = props.address as string | undefined;
  const openingHours = props.opening_hours as string | undefined;
  const category = props.category as string | undefined;

  const categoryLabel = category ? (CATEGORY_LABELS[category] ?? category) : undefined;

  const CATEGORY_LAYER_MAP: Record<string, string> = {
    school: 'schools',
    healthcare: 'healthcare',
    park: 'parks',
    waste: 'waste',
  };
  const layerKey = category ? (CATEGORY_LAYER_MAP[category] ?? 'schools') : 'schools';
  const meta = LAYER_METADATA[layerKey];

  return (
    <div className="text-sm space-y-1 max-w-[220px]">
      <p className="text-[16px] font-semibold leading-tight">
        {name ?? categoryLabel ?? 'Einrichtung'}
      </p>
      {address && (
        <p className="text-[13px]">{address}</p>
      )}
      {openingHours && (
        <p className="text-[13px]">Oeffnungszeiten: {openingHours}</p>
      )}
      {categoryLabel && (
        <p className="text-[11px] text-muted-foreground">{categoryLabel}</p>
      )}
      {meta && (
        <DataSourceSection
          sourceName={meta.sourceName}
          sourceUrl={meta.sourceUrl}
          dataType={meta.dataType}
          timestamp={(props.fetched_at as string) ?? null}
        />
      )}
    </div>
  );
}
