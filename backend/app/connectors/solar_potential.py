"""SolarPotentialConnector: conditional probe for LUBW solar WMS endpoint.

Implements INFR-03: probes the LUBW RIPS-GDI WMS for solar potential layers.
This is an intentional stub/probe connector — no features are upserted.

If the WMS endpoint responds with valid WMS XML containing layer names,
the available layers are logged and the WMS base URL is stored for the
frontend WmsOverlayLayer to use directly.

If the endpoint is unavailable or returns no valid layers, the connector
logs a warning and defers gracefully. This is expected behavior during
development when the endpoint URL is unconfirmed.

Note: INFR-04 (solar rooftop classification) is already addressed by the
Phase 7 EnergyLayer MaStR solar_rooftop classification — no additional
connector is needed for that requirement.

License: LUBW Baden-Wuerttemberg
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

# Candidate LUBW RIPS-GDI WMS endpoint for solar potential layers
_LUBW_SOLAR_WMS_URL = (
    "https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wms/"
    "UIS_0100000003700001/MapServer/WMSServer"
    "?REQUEST=GetCapabilities&SERVICE=WMS"
)


class SolarPotentialConnector(BaseConnector):
    """Probes LUBW WMS for solar potential layer availability.

    This is a conditional/stub connector. It does NOT upsert features.
    Instead it:
    1. Attempts a WMS GetCapabilities request to the LUBW RIPS-GDI endpoint
    2. If the response is valid WMS XML with layers, logs available layers
       and stores the WMS base URL for frontend use
    3. If the response is unavailable, logs a deferral warning and returns

    The frontend solar toggle can conditionally render a WmsOverlayLayer
    using the discovered WMS URL (stored in self.wms_url after a successful
    probe). When enabled=false in town config, the connector is skipped
    entirely by APScheduler.

    Config keys (from ConnectorConfig.config dict):
        wms_url: str — Override WMS base URL (empty string = use default probe URL).
        attribution: str — Attribution string for data provenance.
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        # Class attribute updated after a successful probe
        self.wms_url: str = self.config.config.get("wms_url", "")
        self.available_layers: list[str] = []

    async def fetch(self) -> bytes:
        """Attempt WMS GetCapabilities request.

        Returns:
            WMS GetCapabilities XML response as bytes, or empty bytes if
            the endpoint is unreachable.
        """
        probe_url = self.wms_url if self.wms_url else _LUBW_SOLAR_WMS_URL

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(probe_url)
                if response.status_code != 200:
                    logger.warning(
                        "SolarPotentialConnector: WMS probe returned HTTP %d — "
                        "INFR-03 deferred",
                        response.status_code,
                    )
                    return b""
                return response.content
        except httpx.RequestError as exc:
            logger.warning(
                "SolarPotentialConnector: WMS probe request failed: %s — "
                "INFR-03 deferred",
                exc,
            )
            return b""

    def normalize(self, raw: Any) -> list[Observation]:
        """Return empty list — SolarPotentialConnector produces no observations.

        Args:
            raw: Unused.

        Returns:
            Empty list.
        """
        return []

    def _parse_wms_layers(self, xml_bytes: bytes) -> list[str]:
        """Extract layer names from WMS GetCapabilities XML.

        Args:
            xml_bytes: Raw WMS GetCapabilities XML response.

        Returns:
            List of layer name strings. Empty list if parsing fails or
            no layers found.
        """
        if not xml_bytes:
            return []

        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_bytes)
            # WMS 1.3.0 namespace
            ns = {
                "wms": "http://www.opengis.net/wms",
                "ows": "http://www.opengis.net/ows",
            }

            layers: list[str] = []

            # Try with WMS namespace first
            for layer_elem in root.findall(".//wms:Layer/wms:Name", ns):
                if layer_elem.text:
                    layers.append(layer_elem.text.strip())

            # Fallback: no-namespace search for WMS 1.1.x
            if not layers:
                for layer_elem in root.findall(".//Layer/Name"):
                    if layer_elem.text:
                        layers.append(layer_elem.text.strip())

            return layers

        except Exception as exc:
            logger.warning(
                "SolarPotentialConnector: could not parse WMS XML: %s", exc
            )
            return []

    async def run(self) -> None:
        """Probe LUBW solar WMS and log availability.

        Overrides BaseConnector.run(). This is an intentional probe —
        no features are upserted, no observations are persisted.

        If WMS is available and returns valid layer XML, stores the WMS
        base URL and layer names on the instance for frontend use.
        If WMS is unavailable, logs deferral warning and returns cleanly.
        """
        raw = await self.fetch()

        if not raw:
            logger.warning(
                "Solar potential WMS not available — INFR-03 deferred"
            )
            await self._update_staleness()
            return

        layers = self._parse_wms_layers(raw)

        if not layers:
            logger.warning(
                "SolarPotentialConnector: WMS responded but contained no valid layers — "
                "INFR-03 deferred"
            )
        else:
            # Store WMS base URL for frontend to use as WmsOverlayLayer source
            base_url = _LUBW_SOLAR_WMS_URL.split("?")[0]
            self.wms_url = base_url
            self.available_layers = layers
            logger.info(
                "SolarPotentialConnector: WMS available at %s — %d layers found: %s",
                base_url,
                len(layers),
                ", ".join(layers[:5]),
            )

        await self._update_staleness()
