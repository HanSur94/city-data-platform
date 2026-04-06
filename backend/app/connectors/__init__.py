# Connector package — individual connector modules are imported by name at runtime.
from app.connectors.ladesaeulen import LadesaeulenConnector
from app.connectors.solar_potential import SolarPotentialConnector

__all__ = ["LadesaeulenConnector", "SolarPotentialConnector"]
