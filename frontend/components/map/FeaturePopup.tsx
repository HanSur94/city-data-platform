'use client';
import { Badge } from '@/components/ui/badge';
import FreshnessIndicator from './FreshnessIndicator';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { CrossDomainSection } from '@/components/map/CrossDomainSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import { AQI_TIER_COLORS } from '@/lib/map-styles';
import type { Feature } from 'geojson';

interface FeaturePopupProps {
  feature: Feature;
  lastFetched: Date | null;
}

export default function FeaturePopup({ feature, lastFetched }: FeaturePopupProps) {
  const props = feature.properties ?? {};
  const featureId = (props.feature_id as string) ?? (feature.id as string) ?? null;
  const isAQI = 'aqi' in props || 'pm25' in props;

  if (isAQI) {
    return (
      <div className="text-sm space-y-1 max-w-[200px]">
        <p className="text-[16px] font-semibold leading-tight">
          {props.name ?? 'Luftqualitätssensor'}
        </p>
        {props.pm25 != null && <p className="text-[14px]">PM2.5: {props.pm25} µg/m³</p>}
        {props.pm10 != null && <p className="text-[14px]">PM10: {props.pm10} µg/m³</p>}
        {props.no2 != null  && <p className="text-[14px]">NO₂: {props.no2} µg/m³</p>}
        {props.aqi_tier && (
          <Badge
            style={{
              backgroundColor: AQI_TIER_COLORS[props.aqi_tier as string] ?? '#9e9e9e',
              color: ['good', 'moderate'].includes(props.aqi_tier as string) ? '#000' : '#fff',
            }}
          >
            {props.aqi_tier as string}
          </Badge>
        )}
        {props.aqi == null && (
          <p className="text-[12px] text-muted-foreground">Kein aktueller Messwert</p>
        )}
        <FreshnessIndicator lastFetched={lastFetched} />
        <DataSourceSection
          sourceName={LAYER_METADATA['airQuality'].sourceName}
          sourceUrl={LAYER_METADATA['airQuality'].sourceUrl}
          dataType={LAYER_METADATA['airQuality'].dataType}
          timestamp={(props.measured_at as string) ?? (props.fetched_at as string) ?? null}
        />
        <CrossDomainSection featureId={featureId} ownDomain="air_quality" />
      </div>
    );
  }

  // Transit stop popup
  return (
    <div className="text-sm space-y-1 max-w-[200px]">
      <p className="text-[16px] font-semibold leading-tight">
        {props.stop_name ?? 'Haltestelle'}
      </p>
      {props.route_short_name && (
        <p className="text-[14px]">Linie: {props.route_short_name as string}</p>
      )}
      {props.route_type_color && (
        <p className="text-[12px] text-muted-foreground capitalize">
          Typ: {props.route_type_color === 'bus' ? 'Bus' : props.route_type_color === 'train' ? 'Bahn' : 'Strassenbahn'}
        </p>
      )}
      <FreshnessIndicator lastFetched={lastFetched} />
      <DataSourceSection
        sourceName={LAYER_METADATA['transit'].sourceName}
        sourceUrl={LAYER_METADATA['transit'].sourceUrl}
        dataType={LAYER_METADATA['transit'].dataType}
        timestamp={(props.fetched_at as string) ?? null}
      />
      <CrossDomainSection featureId={featureId} ownDomain="transit" />
    </div>
  );
}
