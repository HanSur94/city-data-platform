'use client';
import { Source, Layer } from 'react-map-gl/maplibre';

interface WmsOverlayLayerProps {
  id: string;
  wmsUrl: string;
  layers: string;
  visible: boolean;
  opacity?: number;
}

export default function WmsOverlayLayer({ id, wmsUrl, layers, visible, opacity = 0.7 }: WmsOverlayLayerProps) {
  const tilesUrl =
    `${wmsUrl}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap` +
    `&LAYERS=${encodeURIComponent(layers)}&STYLES=&FORMAT=image/png&TRANSPARENT=true` +
    `&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256`;

  // Not mounted while hidden: a layer at opacity 0 still requests every tile, and the
  // public WMS servers behind these overlays are slow or failing, which stalls the map.
  if (!visible) return null;

  return (
    <Source id={id} type="raster" tiles={[tilesUrl]} tileSize={256}>
      <Layer id={`${id}-layer`} type="raster" paint={{ 'raster-opacity': opacity }} />
    </Source>
  );
}
