"""
Tests unitarios para Data Cleaner
"""

import pytest
from datetime import datetime
from src.scraper.data_cleaner import DataCleaner


class TestDataCleaner:
    """Tests para DataCleaner"""
    
    @pytest.fixture
    def cleaner(self):
        return DataCleaner()
    
    @pytest.fixture
    def valid_raw_data(self):
        return {
            'timestamp': datetime.now(),
            'total_mwh': 89685,
            'hydro_mwh': 63041,
            'thermal_mwh': 25726,
            'renewable_mwh': 665,
            'import_mwh': 117,
            'export_mwh': 83
        }
    
    def test_cleaner_initialization(self, cleaner):
        """Verifica que cleaner se inicializa"""
        assert cleaner is not None
        assert hasattr(cleaner, 'clean_production_data')
        assert hasattr(cleaner, 'validate_ranges')
    
    def test_clean_production_data_valid(self, cleaner, valid_raw_data):
        """Tests para limpieza de datos válidos"""
        cleaned = cleaner.clean_production_data(valid_raw_data)
        
        assert cleaned is not None
        assert cleaned['total_mwh'] == 89685.0
        assert cleaned['hydro_mwh'] == 63041.0
        assert 'hydro_percentage' in cleaned
        assert cleaned['hydro_percentage'] > 0
    
    def test_clean_production_data_missing_fields(self, cleaner):
        """Tests con campos faltantes"""
        incomplete_data = {
            'timestamp': datetime.now(),
            'total_mwh': 89685,
            'hydro_mwh': 63041
            # Faltan otros campos
        }
        cleaned = cleaner.clean_production_data(incomplete_data)
        # Debería retornar None porque faltan campos requeridos
        assert cleaned is None
    
    def test_clean_production_data_negative_values(self, cleaner):
        """Tests con valores negativos"""
        invalid_data = {
            'timestamp': datetime.now(),
            'total_mwh': 89685,
            'hydro_mwh': -63041,  # Negativo
            'thermal_mwh': 25726,
            'renewable_mwh': 665,
            'import_mwh': 0,
            'export_mwh': 0
        }
        cleaned = cleaner.clean_production_data(invalid_data)
        assert cleaned is None
    
    def test_clean_production_data_type_conversion(self, cleaner):
        """Tests para conversión de tipos"""
        data_with_strings = {
            'timestamp': datetime.now(),
            'total_mwh': '89685',  # String
            'hydro_mwh': '63041',  # String
            'thermal_mwh': 25726.5,
            'renewable_mwh': 665,
            'import_mwh': 117,
            'export_mwh': 83
        }
        cleaned = cleaner.clean_production_data(data_with_strings)
        
        assert cleaned is not None
        assert isinstance(cleaned['total_mwh'], float)
        assert isinstance(cleaned['hydro_mwh'], float)
    
    def test_percentage_calculation(self, cleaner, valid_raw_data):
        """Tests para cálculo de porcentajes"""
        cleaned = cleaner.clean_production_data(valid_raw_data)
        
        assert cleaned is not None
        
        # Los porcentajes deben sumar ~100%
        total_pct = (
            cleaned['hydro_percentage'] +
            cleaned['thermal_percentage'] +
            cleaned['renewable_percentage']
        )
        
        assert 95 <= total_pct <= 105  # Permitir pequeña margen
    
    def test_validate_ranges_valid(self, cleaner, valid_raw_data):
        """Tests para validación de rangos válidos"""
        cleaned = cleaner.clean_production_data(valid_raw_data)
        assert cleaner.validate_ranges(cleaned) == True
    
    def test_validate_ranges_too_high(self, cleaner):
        """Tests para generación muy alta"""
        data = {'total_mwh': 200000}  # Muy alto (fuera del MAX de 150,000)
        assert cleaner.validate_ranges(data) == False
    
    def test_validate_ranges_too_low(self, cleaner):
        """Tests para generación muy baja"""
        data = {'total_mwh': 100}  # Muy bajo
        assert cleaner.validate_ranges(data) == False
    
    def test_sanitize_html(self, cleaner):
        """Tests para sanitización de HTML"""
        # HTML con script
        dirty_html = "<p>Content</p><script>alert('xss')</script>"
        clean_html = cleaner.sanitize_html(dirty_html)
        
        assert "script" not in clean_html.lower() or "<script>" not in clean_html
        assert "Content" in clean_html
    
    def test_detect_outliers_no_historical(self, cleaner):
        """Tests para detección de outliers sin histórico"""
        # Sin histórico, debería retornar True (no se puede validar)
        result = cleaner.detect_outliers(5000, "test_field", None)
        assert result == True
    
    def test_detect_outliers_with_historical(self, cleaner):
        """Tests para detección de outliers con histórico"""
        historical = [5000, 5100, 5200, 5050, 5150]
        
        # Valor normal
        assert cleaner.detect_outliers(5000, "test", historical) == True
        
        # Valor extremo
        assert cleaner.detect_outliers(15000, "test", historical) == False
