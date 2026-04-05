"""StubConnector: a no-op connector used for testing BaseConnector contract.

Does not make any network calls. Returns empty observations.
Used in towns/aalen.yaml as the placeholder connector class during Phase 1.
"""
from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town


class StubConnector(BaseConnector):
    """No-op connector for testing the BaseConnector contract.

    fetch() returns a simple dict with town context.
    normalize() always returns an empty list (no real data).
    """

    async def fetch(self) -> dict:
        return {"status": "ok", "town": self.town.id}

    def normalize(self, raw: dict) -> list[Observation]:
        # Stub returns no observations
        return []
