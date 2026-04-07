'use client';
import { useMemo } from 'react';
import { useFeatureData, useFeatureDataAtPoint } from '@/hooks/useFeatureData';
import type { Feature } from 'geojson';

interface UnifiedBuildingPopupProps {
  feature: Feature;
  longitude: number;
  latitude: number;
  town?: string;
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

/** Map OpenMapTiles building class to German label */
function buildingClassLabel(cls: string | undefined): string | null {
  if (!cls) return null;
  const map: Record<string, string> = {
    residential: 'Wohngebaeude',
    commercial: 'Gewerbegebaeude',
    industrial: 'Industriegebaeude',
    retail: 'Einzelhandel',
    office: 'Buerogebaeude',
    church: 'Kirche',
    school: 'Schule',
    hospital: 'Krankenhaus',
    university: 'Universitaet',
    public: 'Oeffentliches Gebaeude',
    garage: 'Garage',
    shed: 'Schuppen',
    barn: 'Scheune',
    house: 'Wohnhaus',
    apartments: 'Mehrfamilienhaus',
    detached: 'Einfamilienhaus',
    terrace: 'Reihenhaus',
    semidetached_house: 'Doppelhaushaelfte',
  };
  return map[cls] ?? cls;
}

/** Map roof shape tags to German */
function roofShapeLabel(shape: string | undefined): string | null {
  if (!shape) return null;
  const map: Record<string, string> = {
    flat: 'Flachdach',
    gabled: 'Satteldach',
    hipped: 'Walmdach',
    pyramidal: 'Pyramidendach',
    skillion: 'Pultdach',
    half_hipped: 'Kruppwalmdach',
    round: 'Runddach',
    mansard: 'Mansarddach',
    dome: 'Kuppel',
  };
  return map[shape] ?? shape;
}

export default function UnifiedBuildingPopup({
  feature,
  longitude,
  latitude,
  town = 'aalen',
}: UnifiedBuildingPopupProps) {
  const tileProps = feature.properties ?? {};

  // Try to get feature_id from the tile (unlikely for vector tile buildings)
  const featureId = useMemo(() => {
    const id = tileProps.feature_id ?? tileProps.id;
    return id ? String(id) : null;
  }, [tileProps.feature_id, tileProps.id]);

  // Primary: lookup by feature_id if available
  const byId = useFeatureData(featureId);
  // Fallback: reverse-lookup by coordinates
  const byPoint = useFeatureDataAtPoint(
    featureId ? null : longitude,
    featureId ? null : latitude,
    town,
  );

  const data = byId.data ?? byPoint.data;
  const loading = byId.loading || byPoint.loading;
  const error = byId.error ?? byPoint.error;

  // === Building Info from tile properties + DB properties ===
  const dbProps = data?.properties ?? {};

  // Address: try DB first, then tile props
  const street = (dbProps.street as string) ?? (dbProps['addr:street'] as string) ?? (tileProps['addr:street'] as string) ?? null;
  const housenumber = (dbProps.housenumber as string) ?? (dbProps['addr:housenumber'] as string) ?? (tileProps['addr:housenumber'] as string) ?? null;
  const address = (dbProps.address as string)
    ?? (street && housenumber ? `${street} ${housenumber}` : street)
    ?? (tileProps.name as string)
    ?? null;

  // Building type
  const buildingType = buildingClassLabel(
    (dbProps.building_type as string) ?? (dbProps.class as string) ?? (tileProps.class as string) ?? (tileProps.type as string),
  );

  // Height
  const heightM = (tileProps.render_height as number) ?? (dbProps.height as number) ?? null;

  // Roof shape
  const roofShape = roofShapeLabel(
    (dbProps.roof_shape as string) ?? (dbProps['roof:shape'] as string),
  );

  // Year built
  const yearBuilt = (dbProps.year_built as string) ?? (dbProps.start_date as string) ?? (dbProps.baujahr as string) ?? null;

  // Levels / floors
  const levels = (dbProps.levels as number) ?? (tileProps['building:levels'] as number) ?? null;

  // Has any building info to show?
  const hasBuildingInfo = address || buildingType || heightM || roofShape || yearBuilt || levels;

  // === Observation data ===
  const hasObservations = data?.observations && Object.keys(data.observations).length > 0;
  const energyObs = data?.observations?.energy;
  const demographicsObs = data?.observations?.demographics;

  const heatDemand = (energyObs?.values?.heat_demand_kwh as number) ?? (dbProps.heat_demand_kwh as number) ?? null;
  const solarInstalledKw = (energyObs?.values?.solar_installed_kw as number) ?? (dbProps.solar_installed_kw as number) ?? null;
  const solarProduction = (energyObs?.values?.solar_production as number) ?? (dbProps.solar_production as number) ?? null;
  const fernwaermeConnected = (dbProps.fernwaerme_connected as boolean) ?? null;
  const energyClass = (dbProps.energy_class as string) ?? (energyObs?.values?.energy_class as string) ?? null;

  const hasWaerme = heatDemand != null;
  const hasSolar = solarInstalledKw != null || solarProduction != null;
  const hasFernwaerme = fernwaermeConnected != null;
  const hasDemografie = demographicsObs != null;
  const hasEnergie = energyClass != null;
  const hasAnyData = hasBuildingInfo || hasWaerme || hasSolar || hasFernwaerme || hasDemografie || hasEnergie || hasObservations;

  return (
    <div className="text-sm space-y-1 max-w-[320px]">
      {/* Header */}
      <p className="text-[16px] font-semibold leading-tight">
        {buildingType ?? 'Gebaeude'}
      </p>
      {address && (
        <p className="text-[13px] text-muted-foreground">{address}</p>
      )}

      {/* Gebaeude-Info section */}
      {hasBuildingInfo && (
        <>
          <SectionHeader title="Gebaeude-Info" />
          {heightM != null && (
            <DataRow label="Hoehe" value={`${Math.round(heightM)} m`} />
          )}
          {levels != null && (
            <DataRow label="Stockwerke" value={levels} />
          )}
          {roofShape && <DataRow label="Dachform" value={roofShape} />}
          {yearBuilt && <DataRow label="Baujahr" value={yearBuilt} />}
        </>
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

      {/* No data available */}
      {!loading && !error && !hasAnyData && (
        <p className="text-[13px] text-muted-foreground italic mt-1">
          Keine weiteren Daten verfuegbar
        </p>
      )}

      {/* Data sections */}
      {!loading && !error && data && (
        <>
          {hasWaerme && (
            <>
              <SectionHeader title="Waerme" />
              <DataRow label="Waermebedarf" value={`${Math.round(heatDemand!)} kWh/m\u00B2/a`} />
            </>
          )}

          {hasSolar && (
            <>
              <SectionHeader title="Solar" />
              {solarInstalledKw != null && (
                <DataRow label="Installiert" value={`${solarInstalledKw} kW`} />
              )}
              {solarProduction != null && (
                <DataRow label="Aktuelle Produktion" value={`${solarProduction.toFixed(1)} kW`} />
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

      {/* Coordinates footer */}
      <p className="text-[11px] text-muted-foreground/60 mt-1 pt-1 border-t border-border/50">
        {latitude.toFixed(5)}, {longitude.toFixed(5)}
        {data?.semantic_id && (
          <span className="ml-2">{data.semantic_id}</span>
        )}
      </p>
    </div>
  );
}
