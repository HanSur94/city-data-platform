'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface SolarPopupProps {
  feature: Feature;
}

export default function SolarPopup({ feature }: SolarPopupProps) {
  const props = feature.properties ?? {};
  const installationType = props.installation_type as string | undefined;
  const capacityKw = props.capacity_kw as number | undefined;
  const currentOutputKw = props.current_output_kw as number | undefined;
  const irradianceFactor = props.irradiance_factor as number | undefined;
  const commissioningYear = props.commissioning_year as number | string | undefined;

  const title = installationType === 'solar_ground'
    ? 'Solaranlage (Freiflaeche)'
    : 'Solaranlage (Dach)';

  return (
    <div className="text-sm space-y-1 max-w-[240px]">
      <p className="text-[16px] font-semibold leading-tight">
        {title}
      </p>
      {capacityKw != null && (
        <p className="text-[14px]">Installiert: {capacityKw} kW</p>
      )}
      {currentOutputKw != null && (
        <p className="text-[14px]">Aktuelle Leistung: {currentOutputKw.toFixed(1)} kW</p>
      )}
      {irradianceFactor != null && (
        <p className="text-[14px]">
          Auslastung: {Math.round(irradianceFactor * 100)}%
        </p>
      )}
      {commissioningYear != null && (
        <p className="text-[14px]">Inbetriebnahme: {commissioningYear}</p>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['solarGlow'].sourceName}
        sourceUrl={LAYER_METADATA['solarGlow'].sourceUrl}
        dataType={LAYER_METADATA['solarGlow'].dataType}
        timestamp={(props.fetched_at as string) ?? null}
      />
    </div>
  );
}
