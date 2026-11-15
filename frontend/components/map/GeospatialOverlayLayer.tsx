'use client';
import { useEffect } from 'react';
import { useMap } from 'react-map-gl/maplibre';
import WmsOverlayLayer from './WmsOverlayLayer';
import { applyOnStyleLoad } from './applyOnStyleLoad';
import {
  HILLSHADE_LAYER_ID,
  TERRAIN_EXAGGERATION,
  TERRAIN_SOURCE_ID,
} from '@/lib/map-styles';

interface GeospatialOverlayLayerProps {
  cadastralVisible: boolean;
  hillshadeVisible: boolean;
  terrainVisible: boolean;
}

export default function GeospatialOverlayLayer({
  cadastralVisible,
  hillshadeVisible,
  terrainVisible,
}: GeospatialOverlayLayerProps) {
  const { current: mapRef } = useMap();

  // Hillshade relief: the layer is baked (hidden) into every base style; only its
  // visibility is toggled here, and re-applied after every style swap.
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    return applyOnStyleLoad(map, () => {
      if (map.getLayer(HILLSHADE_LAYER_ID)) {
        map.setLayoutProperty(HILLSHADE_LAYER_ID, 'visibility', hillshadeVisible ? 'visible' : 'none');
      }
    });
  }, [mapRef, hillshadeVisible]);

  // 3D terrain: switched imperatively (react-map-gl's terrain prop has no "off" value)
  // and re-applied after every style swap.
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    return applyOnStyleLoad(map, () => {
      if (terrainVisible) {
        if (map.getSource(TERRAIN_SOURCE_ID)) {
          map.setTerrain({ source: TERRAIN_SOURCE_ID, exaggeration: TERRAIN_EXAGGERATION });
        }
      } else if (map.getTerrain()) {
        map.setTerrain(null);
      }
    });
  }, [mapRef, terrainVisible]);

  return (
    <WmsOverlayLayer
      id="cadastral"
      wmsUrl="https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_ALKIS"
      layers="Flurstueck,Gebaeude"
      visible={cadastralVisible}
      opacity={0.7}
    />
  );
}
