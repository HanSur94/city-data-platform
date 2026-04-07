'use client';
import { useMemo } from 'react';
import { useFeatureData } from '@/hooks/useFeatureData';
import type { Feature } from 'geojson';

interface UnifiedBuildingPopupProps {
  feature: Feature;
  longitude: number;
  latitude: number;
}

function SectionHeader({ title }: { title: string }) {
  return (
    <p className="text-[13px] font-semibold text-muted-foreground uppercase tracking-wide mt-2 mb-0.5">
      {title}
    </p>
  );
}

function DataRow({ label, value }: { label: string; value: string | number }) {
  return (
    <p className="text-[13px]">
      <span className="text-muted-foreground">{label}:</span>{' '}
      <span className="font-medium">{value}</span>
    </p>
  );
}

export default function UnifiedBuildingPopup({
  feature,
}: UnifiedBuildingPopupProps) {
  const props = feature.properties ?? {};

  const featureId = useMemo(() => {
    const id = props.feature_id ?? props.id;
    return id ? String(id) : null;
  }, [props.feature_id, props.id]);

  const { data, loading, error } = useFeatureData(featureId);

  // Address / name from vector tile properties or API data
  const address =
    (data?.properties?.address as string) ??
    (props.name as string) ??
    null;

  const hasObservations =
    data?.observations && Object.keys(data.observations).length > 0;

  // Extract observation data by domain
  const energyObs = data?.observations?.energy;
  const demographicsObs = data?.observations?.demographics;

  // Extract from properties or observations
  const heatDemand =
    (energyObs?.values?.heat_demand_kwh as number) ??
    (data?.properties?.heat_demand_kwh as number) ??
    null;

  const solarInstalledKw =
    (energyObs?.values?.solar_installed_kw as number) ??
    (data?.properties?.solar_installed_kw as number) ??
    null;

  const solarProduction =
    (energyObs?.values?.solar_production as number) ??
    (data?.properties?.solar_production as number) ??
    null;

  const fernwaermeConnected =
    (data?.properties?.fernwaerme_connected as boolean) ??
    null;

  const energyClass =
    (data?.properties?.energy_class as string) ??
    (energyObs?.values?.energy_class as string) ??
    null;

  const hasWaerme = heatDemand != null;
  const hasSolar = solarInstalledKw != null || solarProduction != null;
  const hasFernwaerme = fernwaermeConnected != null;
  const hasDemografie = demographicsObs != null;
  const hasEnergie = energyClass != null;

  return (
    <div className="text-sm space-y-1 max-w-[320px]">
      {/* Header */}
      <p className="text-[16px] font-semibold leading-tight">Gebaeude</p>
      {address && (
        <p className="text-[13px] text-muted-foreground">{address}</p>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center gap-2 py-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
          <span className="text-[13px] text-muted-foreground">Lade Daten...</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <p className="text-[13px] text-destructive">{error}</p>
      )}

      {/* No feature_id -- show tile-only info */}
      {!featureId && !loading && (
        <p className="text-[13px] text-muted-foreground italic mt-1">
          Keine Daten verfuegbar
        </p>
      )}

      {/* Data loaded but no observations */}
      {!loading && !error && data && !hasObservations && !hasWaerme && !hasSolar && !hasFernwaerme && !hasEnergie && (
        <p className="text-[13px] text-muted-foreground italic mt-1">
          Keine Daten verfuegbar
        </p>
      )}

      {/* Data sections */}
      {!loading && !error && data && (
        <>
          {hasWaerme && (
            <>
              <SectionHeader title="Waerme" />
              <DataRow
                label="Waermebedarf"
                value={`${Math.round(heatDemand!)} kWh`}
              />
            </>
          )}

          {hasSolar && (
            <>
              <SectionHeader title="Solar" />
              {solarInstalledKw != null && (
                <DataRow label="Installiert" value={`${solarInstalledKw} kW`} />
              )}
              {solarProduction != null && (
                <DataRow
                  label="Produktion"
                  value={`${solarProduction.toFixed(1)} kWh`}
                />
              )}
            </>
          )}

          {hasFernwaerme && (
            <>
              <SectionHeader title="Fernwaerme" />
              <p className="text-[13px]">
                {fernwaermeConnected ? (
                  <span className="text-green-600 font-medium">Angeschlossen</span>
                ) : (
                  <span className="text-muted-foreground">Nicht angeschlossen</span>
                )}
              </p>
            </>
          )}

          {hasDemografie && (
            <>
              <SectionHeader title="Demografie" />
              {Object.entries(demographicsObs!.values).map(([key, val]) => (
                <DataRow key={key} label={key} value={String(val)} />
              ))}
            </>
          )}

          {hasEnergie && (
            <>
              <SectionHeader title="Energie" />
              <DataRow label="Energieklasse" value={energyClass!} />
            </>
          )}
        </>
      )}
    </div>
  );
}
