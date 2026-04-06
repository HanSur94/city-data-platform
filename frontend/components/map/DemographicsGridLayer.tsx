'use client';
import WmsOverlayLayer from './WmsOverlayLayer';

export type DemographicMetric = 'population' | 'age' | 'rent' | 'heating';

interface DemographicsGridLayerProps {
  town: string;
  visible: boolean;
  activeMetric?: DemographicMetric;
}

const ZENSUS_WMS_URL = 'https://atlas.zensus2022.de/geoserver/ows';

/** Zensus 2022 WMS layer names per metric */
const METRIC_LAYERS: Record<DemographicMetric, string> = {
  population: 'Bevoelkerung:Einwohner_100m_Gitter',
  age: 'Bevoelkerung:Durchschnittsalter_100m_Gitter',
  rent: 'Gebaeude_Wohnungen:Durchschnittliche_Wohnungsmiete_100m_Gitter',
  heating: 'Gebaeude_Wohnungen:Heizungsart_100m_Gitter',
};

/**
 * Zensus 2022 demographics grid overlay.
 * Renders a WMS layer for 100m grid cells with the selected demographic metric.
 */
export default function DemographicsGridLayer({
  visible,
  activeMetric = 'population',
}: DemographicsGridLayerProps) {
  if (!visible) return null;

  return (
    <>
      {(Object.keys(METRIC_LAYERS) as DemographicMetric[]).map((metric) => (
        <WmsOverlayLayer
          key={metric}
          id={`demographics-grid-${metric}`}
          wmsUrl={ZENSUS_WMS_URL}
          layers={METRIC_LAYERS[metric]}
          visible={activeMetric === metric}
          opacity={0.6}
        />
      ))}
    </>
  );
}
