'use client';
import type { Feature } from 'geojson';

interface CyclingPopupProps {
  feature: Feature;
}

const INFRA_TYPE_COLORS: Record<string, string> = {
  separated: '#1a7c28',
  lane: '#5cb85c',
  advisory: '#f0ad4e',
  shared: '#e67e22',
  none: '#d9534f',
};

const INFRA_TYPE_LABELS: Record<string, string> = {
  separated: 'Getrennter Radweg',
  lane: 'Radfahrstreifen',
  advisory: 'Schutzstreifen',
  shared: 'Gemeinsamer Weg',
  none: 'Keine Radinfrastruktur',
};

export default function CyclingPopup({ feature }: CyclingPopupProps) {
  const props = feature.properties ?? {};
  const roadName = (props.road_name as string | null) || 'Unbenannt';
  const infraType = props.infra_type as string | undefined;

  return (
    <div className="text-sm space-y-1 max-w-[220px]">
      <p className="text-[16px] font-semibold leading-tight">{roadName}</p>
      {infraType && (
        <p className="text-[13px] flex items-center gap-1.5">
          <span
            className="inline-block w-3 h-3 rounded-full"
            style={{ background: INFRA_TYPE_COLORS[infraType] ?? '#999' }}
          />
          {INFRA_TYPE_LABELS[infraType] ?? infraType}
        </p>
      )}
      <p className="text-[11px] text-muted-foreground mt-1">Quelle: OpenStreetMap (cycling)</p>
    </div>
  );
}
