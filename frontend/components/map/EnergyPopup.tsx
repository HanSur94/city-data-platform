'use client';
import type { Feature } from 'geojson';

interface EnergyPopupProps {
  feature: Feature;
}

const INSTALLATION_TYPE_LABELS: Record<string, string> = {
  solar_rooftop: 'Solaranlage (Dach)',
  solar_ground: 'Solaranlage (Freifläche)',
  wind: 'Windkraftanlage',
  battery: 'Batteriespeicher',
};

export default function EnergyPopup({ feature }: EnergyPopupProps) {
  const props = feature.properties ?? {};
  const installationType = props.installation_type as string | undefined;
  const capacityKw = props.capacity_kw as number | undefined;
  const commissioningYear = props.commissioning_year as number | string | undefined;
  const operator = props.operator as string | undefined;
  const municipality = props.municipality as string | undefined;

  const typeLabel = installationType
    ? (INSTALLATION_TYPE_LABELS[installationType] ?? installationType)
    : 'Energieanlage';

  const titleText = capacityKw != null
    ? `${typeLabel} — ${capacityKw} kW`
    : typeLabel;

  return (
    <div className="text-sm space-y-1 max-w-[200px]">
      <p className="text-[16px] font-semibold leading-tight">
        {titleText}
      </p>
      {capacityKw != null && (
        <p className="text-[14px]">Leistung: {capacityKw} kW</p>
      )}
      {commissioningYear != null && (
        <p className="text-[14px]">Inbetriebnahme: {commissioningYear}</p>
      )}
      {operator && (
        <p className="text-[12px] text-muted-foreground">{operator}</p>
      )}
      {municipality && (
        <p className="text-[12px] text-muted-foreground">{municipality}</p>
      )}
    </div>
  );
}
