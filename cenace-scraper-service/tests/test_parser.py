"""
Tests unitarios para HTML Parser
"""

import pytest
from datetime import datetime
from src.scraper.html_parser import CENACEHTMLParser


class TestCENACEHTMLParser:
    """Tests para CENACEHTMLParser"""
    
    @pytest.fixture
    def parser(self):
        return CENACEHTMLParser()
    
    @pytest.fixture
    def sample_html(self):
        """HTML de ejemplo (simulado)"""
        return """
        <html>
            <body>
                <table>
                    <tr><td>PRODUCCIÓN ENERGÉTICA (MWh)</td></tr>
                    <tr><td>Total</td><td>89685</td></tr>
                    <tr><td>Hidráulica</td><td>63041</td></tr>
                    <tr><td>Térmica</td><td>25726</td></tr>
                    <tr><td>Renovable</td><td>665</td></tr>
                    <tr><td>Importación</td><td>117</td></tr>
                    <tr><td>Exportación</td><td>83</td></tr>
                </table>
            </body>
        </html>
        """
    
    def test_parser_initialization(self, parser):
        """Verifica que parser se inicializa"""
        assert parser is not None
        assert hasattr(parser, 'parse_production_summary')
        assert hasattr(parser, 'validate_data')
    
    def test_extract_number(self, parser):
        """Tests para extracción de números"""
        
        # Test números simples
        assert parser._extract_number("100") == 100.0
        assert parser._extract_number("100.5") == 100.5
        
        # Test números con comas (formato ES)
        assert parser._extract_number("1.000") == 1000.0
        assert parser._extract_number("63.041") == 63041.0
        
        # Test números con comas como decimal
        assert parser._extract_number("3,5") == 3.5
        
        # Test strings complejos
        assert parser._extract_number("Total: 89,685 MWh") == 89685.0
        assert parser._extract_number("Producción 2.400 MW") == 2400.0
        
        # Test None/invalid
        assert parser._extract_number(None) is None
        assert parser._extract_number("") is None
        assert parser._extract_number("No tiene números") is None
    
    def test_infer_plant_type(self, parser):
        """Tests para inferencia de tipo de central"""
        
        # Hidroeléctrica
        assert parser._infer_plant_type("Mazar Hidroeléctrica") == "HYDRO"
        assert parser._infer_plant_type("Paute Hidro") == "HYDRO"
        assert parser._infer_plant_type("Represa Coca Codo") == "HYDRO"
        
        # Térmica
        assert parser._infer_plant_type("Termo Gas Machala") == "THERMAL"
        assert parser._infer_plant_type("Central Térmica Quito") == "THERMAL"
        
        # Renovable
        assert parser._infer_plant_type("Parque Eólico") == "RENEWABLE"
        assert parser._infer_plant_type("Solar Fotovoltaica") == "RENEWABLE"
        
        # Otro
        assert parser._infer_plant_type("Central Desconocida") == "OTHER"
    
    def test_parse_production_summary(self, parser, sample_html):
        """Tests para parse_production_summary"""
        data = parser.parse_production_summary(sample_html)
        
        assert data is not None
        assert 'total_mwh' in data
        assert 'hydro_mwh' in data
        assert 'thermal_mwh' in data
        assert 'renewable_mwh' in data
        assert 'timestamp' in data
    
    def test_parse_production_summary_empty(self, parser):
        """Tests con HTML vacío"""
        data = parser.parse_production_summary("<html></html>")
        assert data is None
    
    def test_validate_data_valid(self, parser):
        """Tests para validación de datos válidos"""
        data = {
            'total_mwh': 89685,
            'hydro_mwh': 63041,
            'thermal_mwh': 25726,
            'renewable_mwh': 665,
            'import_mwh': 0,
            'export_mwh': 0
        }
        assert parser.validate_data(data) == True
    
    def test_validate_data_missing_fields(self, parser):
        """Tests para datos incompletos"""
        data = {
            'total_mwh': 89685,
            'hydro_mwh': 63041
        }
        assert parser.validate_data(data) == False
    
    def test_validate_data_negative_values(self, parser):
        """Tests para valores negativos"""
        data = {
            'total_mwh': 89685,
            'hydro_mwh': -63041,  # Negativo
            'thermal_mwh': 25726,
            'renewable_mwh': 665,
            'import_mwh': 0,
            'export_mwh': 0
        }
        assert parser.validate_data(data) == False
