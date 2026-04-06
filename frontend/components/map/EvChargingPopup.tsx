'use client';
import { DataSourceSection } from '@/components/map/DataSourceSection';
import { LAYER_METADATA } from '@/lib/layer-metadata';
import type { Feature } from 'geojson';

interface EvChargingPopupProps {
  feature: Feature;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  AVAILABLE: { label: 'Verfuegbar', color: 'bg-green-500' },
  OCCUPIED: { label: 'Belegt', color: 'bg-red-500' },
  INOPERATIVE: { label: 'Ausser Betrieb', color: 'bg-gray-400' },
  UNKNOWN: { label: 'Unbekannt', color: 'bg-gray-400' },
};

function PowerClassLabel({ powerKw, powerClass }: { powerKw?: number; powerClass?: string }) {
  if (powerClass === 'dc_fast') return <span>DC Schnellladen ({powerKw ?? '?'} kW)</span>;
  if (powerClass === 'ac_fast') return <span>AC ({powerKw ?? 22} kW)</span>;
  if (powerClass === 'ac_slow') return <span>AC ({powerKw ?? 11} kW)</span>;
  if (powerKw != null) return <span>{powerKw} kW</span>;
  return null;
}

export default function EvChargingPopup({ feature }: EvChargingPopupProps) {
  const props = feature.properties ?? {};
  const source = props.source as string | undefined;

  // OCPDB live data path
  if (source === 'ocpdb') {
    const operator = props.operator as string | undefined;
    const address = props.address as string | undefined;
    const status = props.status as string | undefined;
    const powerKw = props.power_kw as number | undefined;
    const powerClass = props.power_class as string | undefined;
    const connectorTypes = props.connector_types as string | string[] | undefined;
    const evseCount = props.evse_count as number | undefined;

    const statusInfo = status ? STATUS_LABELS[status] ?? STATUS_LABELS.UNKNOWN : null;

    const connectorDisplay = Array.isArray(connectorTypes)
      ? connectorTypes.join(', ')
      : typeof connectorTypes === 'string'
      ? connectorTypes
      : undefined;

    return (
      <div className="text-sm space-y-1 max-w-[240px]">
        <p className="text-[16px] font-semibold leading-tight">
          {operator ?? 'E-Ladestation'}
        </p>
        {address && (
          <p className="text-[13px]">{address}</p>
        )}
        {statusInfo && (
          <p className="text-[13px] flex items-center gap-1.5">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${statusInfo.color}`} />
            {statusInfo.label}
          </p>
        )}
        <PowerClassLabel powerKw={powerKw} powerClass={powerClass} />
        {connectorDisplay && (
          <p className="text-[13px]">
            <span className="font-medium">Steckertypen:</span> {connectorDisplay}
          </p>
        )}
        {evseCount != null && (
          <p className="text-[13px]">
            <span className="font-medium">Ladepunkte:</span> {evseCount}
          </p>
        )}
        <DataSourceSection
          sourceName={LAYER_METADATA['evCharging'].sourceName}
          sourceUrl={LAYER_METADATA['evCharging'].sourceUrl}
          dataType={LAYER_METADATA['evCharging'].dataType}
          timestamp={(props.fetched_at as string) ?? null}
        />
      </div>
    );
  }

  // Legacy BNetzA data path (existing behavior preserved)
  const operator = props.operator as string | undefined;
  const address = props.address as string | undefined;
  const chargingType = props.charging_type as string | undefined;
  const plugTypes = props.plug_types as string | string[] | undefined;
  const maxPowerKw = props.max_power_kw as number | undefined;
  const chargingPoints = props.charging_points as number | undefined;

  const chargingTypeLabel = chargingType === 'fast'
    ? 'Schnellladen'
    : chargingType === 'normal'
    ? 'Normalladen'
    : chargingType ?? undefined;

  const plugTypesDisplay = Array.isArray(plugTypes)
    ? plugTypes.join(', ')
    : typeof plugTypes === 'string'
    ? plugTypes
    : undefined;

  return (
    <div className="text-sm space-y-1 max-w-[240px]">
      <p className="text-[16px] font-semibold leading-tight">
        {operator ?? 'E-Ladestation'}
      </p>
      {address && (
        <p className="text-[13px]">{address}</p>
      )}
      {chargingTypeLabel && (
        <p className="text-[13px]">{chargingTypeLabel}</p>
      )}
      {plugTypesDisplay && (
        <p className="text-[13px]">
          <span className="font-medium">Steckertypen:</span> {plugTypesDisplay}
        </p>
      )}
      {maxPowerKw != null && (
        <p className="text-[13px]">
          <span className="font-medium">Leistung:</span> {maxPowerKw} kW
        </p>
      )}
      {chargingPoints != null && (
        <p className="text-[13px]">
          <span className="font-medium">Ladepunkte:</span> {chargingPoints}
        </p>
      )}
      <DataSourceSection
        sourceName={LAYER_METADATA['evCharging'].sourceName}
        sourceUrl={LAYER_METADATA['evCharging'].sourceUrl}
        dataType={LAYER_METADATA['evCharging'].dataType}
        timestamp={(props.fetched_at as string) ?? null}
      />
    </div>
  );
}
