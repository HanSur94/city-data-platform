'use client';
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
      <p className="text-[11px] text-muted-foreground">Baustelle (OSM)</p>
    </div>
  );
}
