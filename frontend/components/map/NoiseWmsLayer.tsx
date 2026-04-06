'use client';
import WmsOverlayLayer from './WmsOverlayLayer';

interface NoiseWmsLayerProps {
  visible: boolean;
  noiseMetric?: 'lden' | 'lnight';
}

const LUBW_WMS_URL =
  'https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wms/UIS_0100000017200001/MapServer/WMSServer';

/**
 * LUBW road noise (Strassenlaerm) WMS overlay.
 * Renders two WmsOverlayLayer instances (LDEN + LNight) to avoid tile reload on toggle.
 * Color bands are pre-styled by the WMS: green <55dB, yellow 55-65, orange 65-70, red 70-75, purple >75.
 */
export default function NoiseWmsLayer({ visible, noiseMetric = 'lden' }: NoiseWmsLayerProps) {
  if (!visible) return null;

  return (
    <>
      <WmsOverlayLayer
        id="road-noise-lden"
        wmsUrl={LUBW_WMS_URL}
        layers="0"
        visible={noiseMetric === 'lden'}
        opacity={0.55}
      />
      <WmsOverlayLayer
        id="road-noise-lnight"
        wmsUrl={LUBW_WMS_URL}
        layers="2"
        visible={noiseMetric === 'lnight'}
        opacity={0.55}
      />
    </>
  );
}
