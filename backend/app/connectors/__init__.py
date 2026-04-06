# Connector package — individual connector modules are imported by name at runtime.
from app.connectors.ladesaeulen import LadesaeulenConnector
from app.connectors.solar_potential import SolarPotentialConnector
from app.connectors.wegweiser_kommune import WegweiserKommuneConnector
from app.connectors.statistik_bw import StatistikBWConnector
from app.connectors.zensus import ZensusConnector
from app.connectors.bundesagentur import BundesagenturConnector

__all__ = [
    "LadesaeulenConnector",
    "SolarPotentialConnector",
    "WegweiserKommuneConnector",
    "StatistikBWConnector",
    "ZensusConnector",
    "BundesagenturConnector",
]
