"""
Tests unitarios para HTML Parser
"""

import pytest
from src.scraper.html_parser import CENACEHTMLParser, parse_cenace_number


class TestCENACEHTMLParser:
    """Tests para CENACEHTMLParser"""
    
    @pytest.fixture
    def parser(self):
        return CENACEHTMLParser()
    
    @pytest.fixture
    def sample_html(self):
        """HTML de ejemplo con estructura real simplificada"""
        return """
        <html>
            <body>
                <div class="tab-content active">
                    <div class="resumen-box total"><div>PRODUCCIÓN TOTAL</div><div>92 026</div></div>
                    <div class="resumen-box hidraulica"><div>HIDRÁULICA</div><div>63 022</div></div>
                    <div class="resumen-box otra"><div>TÉRMICA</div><div>28 054</div></div>
                    <div class="resumen-box noconvencional"><div>R. NO CONVENCIONAL</div><div>668</div></div>
                    <div class="resumen-box importacion"><div>IMPORTACIÓN</div><div>72</div></div>
                    <div class="resumen-box exportacion"><div>EXPORTACIÓN</div><div>94</div></div>
                    <script type="text/javascript">
                        Plotly.newPlot(
                            "graph1",
                            [{"type":"bar","name":"Coca Codo","y":[21372]}],
                            {}
                        )
                    </script>
                    <script type="text/javascript">
                        Plotly.newPlot(
                            "graph2",
                            [
                                {"name":"Hidráulica","x":["00:00","00:30"],"y":[1000,1100],"stackgroup":"one"},
                                {"name":"Térmica","x":["00:00","00:30"],"y":[500,550],"stackgroup":"one"},
                                {"name":"Renovable","x":["00:00","00:30"],"y":[100,110],"stackgroup":"one"},
                                {"name":"Importación","x":["00:00","00:30"],"y":[10,10],"stackgroup":"one"},
                                {"name":"Exportación","x":["00:00","00:30"],"y":[5,6],"stackgroup":"one"},
                                {"name":"PRODUCCIÓN TOTAL","x":["00:00","00:30"],"y":[1610,1770]},
                                {"name":"DEMANDA NACIONAL","x":["00:00","00:30"],"y":[1600,1760]}
                            ],
                            {}
                        )
                    </script>
                </div>
            </body>
        </html>
        """
    
    def test_parser_initialization(self, parser):
        """Verifica que parser se inicializa"""
        assert parser is not None
        assert hasattr(parser, 'parse_production_summary')
        assert hasattr(parser, 'validate_data')
    
    def test_parse_cenace_number(self):
        """Tests para parseo de números formato CENACE"""
        assert parse_cenace_number("92 026") == 92026.0
        assert parse_cenace_number("0.727") == 0.727
        assert parse_cenace_number("3,5") == 3.5
        assert parse_cenace_number("") is None
        assert parse_cenace_number("sin numero") is None
    
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

    def test_parse_plant_details(self, parser, sample_html):
        """Tests para extracción de plantas desde Plotly"""
        plants = parser.parse_plant_details(sample_html)
        assert len(plants) == 1
        assert plants[0]["plant_name"] == "Coca Codo"
        assert plants[0]["plant_id"] == "COCA_CODO"

    def test_parse_hourly_curve(self, parser, sample_html):
        """Tests para curva horaria con resolución de 30 minutos"""
        curve = parser.parse_hourly_curve(sample_html)
        assert len(curve) == 2
        assert curve[0]["hour"] == 0
        assert curve[0]["minute"] == 0
        assert curve[1]["minute"] == 30
        assert curve[0]["demand_mw"] == 1600
    
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
