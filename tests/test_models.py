"""
Tests unitarios para modelos de datos
"""
import pytest
from src.models.power_plant import PowerPlant, PlantType, OperationalStatus


class TestPowerPlant:
    """Tests para el modelo PowerPlant"""

    def test_power_plant_creation(self):
        """Test: crear una central eléctrica"""
        plant = PowerPlant(
            id="test_1",
            name="Test Plant",
            plant_type=PlantType.HYDRO,
            latitude=-1.0,
            longitude=-78.0,
            installed_capacity_mw=100,
            available_capacity_mw=100,
            status=OperationalStatus.ONLINE,
            region="Sierra",
            operator="Test Operator"
        )

        assert plant.id == "test_1"
        assert plant.name == "Test Plant"
        assert plant.plant_type == PlantType.HYDRO
        assert plant.installed_capacity_mw == 100

    def test_power_plant_get_output(self):
        """Test: obtener potencia de salida según estado"""
        plant_online = PowerPlant(
            id="test_2",
            name="Online Plant",
            plant_type=PlantType.THERMAL,
            latitude=-1.0,
            longitude=-78.0,
            installed_capacity_mw=150,
            available_capacity_mw=140,
            status=OperationalStatus.ONLINE,
            region="Costa",
            operator="Operator"
        )

        assert plant_online.get_output_mw() == 140

    def test_power_plant_get_output_offline(self):
        """Test: planta offline retorna 0"""
        plant_offline = PowerPlant(
            id="test_3",
            name="Offline Plant",
            plant_type=PlantType.WIND,
            latitude=-1.0,
            longitude=-78.0,
            installed_capacity_mw=50,
            available_capacity_mw=50,
            status=OperationalStatus.OFFLINE,
            region="Costa",
            operator="Operator"
        )

        assert plant_offline.get_output_mw() == 0.0

    def test_power_plant_is_online(self):
        """Test: verificar si central está en línea"""
        plant = PowerPlant(
            id="test_4",
            name="Test",
            plant_type=PlantType.SOLAR,
            latitude=-1.0,
            longitude=-78.0,
            installed_capacity_mw=25,
            available_capacity_mw=20,
            status=OperationalStatus.ONLINE,
            region="Sierra",
            operator="Operator"
        )

        assert plant.is_online() is True

    def test_power_plant_all_types(self):
        """Test: todos los tipos de centrales"""
        for plant_type in [PlantType.HYDRO, PlantType.THERMAL, PlantType.WIND, PlantType.SOLAR]:
            plant = PowerPlant(
                id=f"test_{plant_type.value}",
                name=f"Test {plant_type.value}",
                plant_type=plant_type,
                latitude=-1.0,
                longitude=-78.0,
                installed_capacity_mw=100,
                available_capacity_mw=100,
                status=OperationalStatus.ONLINE,
                region="Test",
                operator="Test Operator"
            )
            assert plant.plant_type == plant_type
            assert plant.is_online() is True
