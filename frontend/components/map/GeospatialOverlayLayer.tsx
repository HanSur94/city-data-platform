'use client';
import WmsOverlayLayer from './WmsOverlayLayer';

interface GeospatialOverlayLayerProps {
  cadastralVisible: boolean;
  hillshadeVisible: boolean;
}

export default function GeospatialOverlayLayer({
  cadastralVisible,
  hillshadeVisible,
}: GeospatialOverlayLayerProps) {
  return (
    <>
      <WmsOverlayLayer
        id="cadastral"
        wmsUrl="https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_ALKIS"
        layers="Flurstueck,Gebaeude"
        visible={cadastralVisible}
        opacity={0.7}
      />
      <WmsOverlayLayer
        id="hillshade"
        wmsUrl="https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DGM_Schummerung"
        layers="Schummerung"
        visible={hillshadeVisible}
        opacity={0.5}
      />
    </>
  );
}
