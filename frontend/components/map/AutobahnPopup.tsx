'use client';
import { Badge } from '@/components/ui/badge';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface AutobahnPopupProps {
  feature: Feature;
}

export default function AutobahnPopup({ feature }: AutobahnPopupProps) {
  const props = feature.properties ?? {};
  const type = props.type as string | undefined;
  const title = props.title as string | undefined;
  const description = props.description as string | undefined;
  const extent = props.extent as string | undefined;
  const isBlocked = props.is_blocked as boolean | undefined;

  const typeLabel = type === 'closure' ? 'Sperrung' : 'Baustelle';

  return (
    <div className="text-sm space-y-1 max-w-[200px]">
      <p className="text-[16px] font-semibold leading-tight">
        {typeLabel}
      </p>
      {title && <p className="text-[14px] font-medium">{title}</p>}
      {description && (
        <p className="text-[14px] text-muted-foreground">{description}</p>
      )}
      {extent && (
        <p className="text-[14px]">Umleitung: {extent}</p>
      )}
      {isBlocked != null && (
        <Badge
          style={{
            backgroundColor: isBlocked ? '#ef4444' : '#22c55e',
            color: '#fff',
          }}
        >
          {isBlocked ? 'Gesperrt' : 'Offen'}
        </Badge>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['autobahn'].sourceName}
        sourceUrl={LAYER_METADATA['autobahn'].sourceUrl}
        dataType={LAYER_METADATA['autobahn'].dataType}
        timestamp={(props.fetched_at as string) ?? null}
      />
    </div>
  );
}
