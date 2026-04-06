'use client';
import type { Feature } from 'geojson';

interface EvChargingPopupProps {
  feature: Feature;
}

export default function EvChargingPopup({ feature }: EvChargingPopupProps) {
  const props = feature.properties ?? {};
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
    </div>
  );
}
