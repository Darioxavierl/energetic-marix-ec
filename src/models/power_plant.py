"""
Modelos de datos para centrales eléctricas
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PlantType(str, Enum):
    """Tipos de centrales eléctricas"""
    HYDRO = "HYDRO"
    THERMAL = "THERMAL"
    WIND = "WIND"
    SOLAR = "SOLAR"


class OperationalStatus(str, Enum):
    """Estados operacionales de una central"""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"


@dataclass
class PowerPlant:
    """
    Modelo de Central Eléctrica

    Atributos:
        id: Identificador único
        name: Nombre de la central
        plant_type: Tipo de central (HYDRO, THERMAL, WIND, SOLAR)
        latitude: Latitud (WGS84)
        longitude: Longitud (WGS84)
        installed_capacity_mw: Potencia instalada en MW
        available_capacity_mw: Potencia disponible actualmente en MW
        status: Estado operacional
        region: Región del Ecuador
        operator: Operador/Empresa responsable
    """
    id: str
    name: str
    plant_type: PlantType
    latitude: float
    longitude: float
    installed_capacity_mw: float
    available_capacity_mw: float
    status: OperationalStatus
    region: str
    operator: str

    def get_output_mw(self) -> float:
        """Retorna potencia de salida según disponibilidad y estado"""
        if self.status == OperationalStatus.ONLINE:
            return self.available_capacity_mw
        return 0.0

    def is_online(self) -> bool:
        """Verifica si la central está en línea"""
        return self.status == OperationalStatus.ONLINE

    def __repr__(self) -> str:
        return (
            f"PowerPlant({self.name}, {self.plant_type.value}, "
            f"{self.installed_capacity_mw}MW, {self.status.value})"
        )
