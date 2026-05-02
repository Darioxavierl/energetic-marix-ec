"""
Parser HTML para CENACE
Extrae datos de: https://www.cenace.gob.ec/info-operativa/InformacionOperativa.htm

Estructura real de la página (descubierta 2026-05-01):
- Datos en <div class="resumen-box [clase]"> dentro de .tab-content.active
- Gráficos Plotly con datos JSON embebidos en <script>
- Tab 0 = Producción tiempo real
- Tab 1 = Demanda tiempo real
- Tab 2 = Información operativa diaria
- Tab 3 = Acumulada mensual
- Tab 4 = Acumulada anual
"""

import re
import json
import struct
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from src.utils.logger import logger


def normalize_text(text: str) -> str:
    """Normaliza texto: lowercase y elimina acentos"""
    text = text.lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def parse_cenace_number(text: str) -> Optional[float]:
    """
    Convierte números con formato CENACE a float.
    Maneja: '92 026', '92&nbsp;026', '4 328', '668', '0.727'
    """
    if not text:
        return None
    # Eliminar &nbsp; y espacios normales (CENACE usa espacio como separador de miles)
    clean = text.replace('\xa0', '').replace(' ', '').replace(',', '.')
    clean = clean.strip()
    try:
        return float(clean)
    except ValueError:
        return None


class CENACEHTMLParser:
    """Parsea HTML de CENACE — estructura de divs con clase resumen-box"""

    def __init__(self):
        self.logger = logger

    def parse_production_summary(self, html: str) -> Optional[Dict]:
        """
        Extrae PRODUCCIÓN ENERGÉTICA (MWh) del tab 0 (Producción Tiempo Real).

        Retorna:
        {
            "timestamp": datetime,
            "total_mwh": 92026.0,
            "hydro_mwh": 63022.0,
            "thermal_mwh": 28054.0,
            "renewable_mwh": 668.0,
            "import_mwh": 72.0,
            "export_mwh": 94.0,
        }
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # El tab de producción es el primero (.tab-content.active o el primero de todos)
            # Todos los tabs están en el HTML; el primero contiene producción tiempo real
            tab_contents = soup.find_all('div', class_='tab-content')

            if not tab_contents:
                self.logger.warning("No se encontraron .tab-content en el HTML")
                return None

            # Tab 0 = PRODUCCIÓN TIEMPO REAL
            prod_tab = tab_contents[0]

            data = self._extract_resumen_boxes(prod_tab)

            if not data.get('total_mwh'):
                self.logger.warning("No se encontró PRODUCCIÓN TOTAL en el tab de producción")
                return None

            data['timestamp'] = datetime.now()
            self.logger.debug(f"Datos de producción extraídos: {data}")
            return data

        except Exception as e:
            self.logger.error(f"Error parseando producción: {e}")
            return None

    def parse_demand_summary(self, html: str) -> Optional[Dict]:
        """
        Extrae DEMANDA (MW) del tab 1 (Demanda Tiempo Real).

        Retorna:
        {
            "timestamp": datetime,
            "demand_total_mw": 4328.0,
            "demand_cnel_mw": 3138.0,
            "demand_empresas_mw": 1190.0,
        }
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            tab_contents = soup.find_all('div', class_='tab-content')

            if len(tab_contents) < 2:
                self.logger.warning("Tab de demanda (índice 1) no encontrado")
                return None

            demand_tab = tab_contents[1]
            boxes = demand_tab.find_all('div', class_='resumen-box')

            data = {'timestamp': datetime.now()}
            for box in boxes:
                divs = box.find_all('div', recursive=False)
                if len(divs) < 2:
                    continue
                label = divs[0].get_text(strip=True)
                value_text = divs[1].get_text(strip=True)
                value = parse_cenace_number(value_text)

                label_norm = normalize_text(label)
                if 'demanda total' in label_norm or 'total' in label_norm:
                    data['demand_total_mw'] = value
                elif 'cnel' in label_norm:
                    data['demand_cnel_mw'] = value
                elif 'empresa' in label_norm or 'anterior' in label_norm:
                    data['demand_empresas_mw'] = value

            return data if data.get('demand_total_mw') else None

        except Exception as e:
            self.logger.error(f"Error parseando demanda: {e}")
            return None

    def parse_plant_details(self, html: str) -> List[Dict]:
        """
        Extrae detalle de plantas desde los gráficos Plotly embebidos en el tab 0.
        Los datos están en JSON dentro de <script> que llama a Plotly.newPlot().
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            tab_contents = soup.find_all('div', class_='tab-content')
            if not tab_contents:
                return []

            prod_tab = tab_contents[0]
            plants_map: Dict[str, Dict] = {}

            # Buscar todos los scripts con Plotly.newPlot dentro del tab de producción
            scripts = prod_tab.find_all('script', type='text/javascript')
            for script in scripts:
                script_text = script.get_text()
                if 'Plotly.newPlot' not in script_text:
                    continue
                plants_from_script = self._extract_plants_from_plotly_script(script_text)
                for plant in plants_from_script:
                    plant_id = plant["plant_id"]
                    existing = plants_map.get(plant_id)
                    if existing is None or plant["mwh"] > existing["mwh"]:
                        plants_map[plant_id] = plant

            plants = list(plants_map.values())

            self.logger.debug(f"Encontradas {len(plants)} centrales en gráficos Plotly")
            return plants

        except Exception as e:
            self.logger.error(f"Error parseando detalles de plantas: {e}")
            return []

    def parse_hourly_curve(self, html: str) -> List[Dict]:
        """
        Extrae la curva horaria de generación/demanda del gráfico Plotly de líneas.
        El gráfico tiene series: Hidráulica, Renovable, Importación, Térmica, Exportación,
        PRODUCCIÓN TOTAL, DEMANDA NACIONAL — con timestamps cada 30 min.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            tab_contents = soup.find_all('div', class_='tab-content')
            if not tab_contents:
                return []

            prod_tab = tab_contents[0]
            scripts = prod_tab.find_all('script', type='text/javascript')

            for script in scripts:
                script_text = script.get_text()
                # El gráfico de curva horaria tiene 'stackgroup' y 'DEMANDA NACIONAL'
                if 'DEMANDA NACIONAL' not in script_text or 'stackgroup' not in script_text:
                    continue
                return self._extract_hourly_from_plotly_script(script_text)

            return []

        except Exception as e:
            self.logger.error(f"Error parseando curva horaria: {e}")
            return []

    def validate_data(self, data: Dict) -> bool:
        """Valida coherencia de datos de producción"""
        try:
            if not data:
                return False

            required_fields = ['total_mwh', 'hydro_mwh', 'thermal_mwh', 'renewable_mwh']
            for field in required_fields:
                if field not in data:
                    self.logger.warning(f"Campo faltante: {field}")
                    return False
                if data.get(field, 0) < 0:
                    self.logger.warning(f"Valor negativo: {field} = {data[field]}")
                    return False

            # Verificar que suma de fuentes ≈ total (tolerancia 10%)
            sources_sum = (
                data.get('hydro_mwh', 0) +
                data.get('thermal_mwh', 0) +
                data.get('renewable_mwh', 0) +
                data.get('import_mwh', 0)
            )
            total = data.get('total_mwh', 0)
            if sources_sum > 0 and total > 0:
                diff_percent = abs((sources_sum - total) / sources_sum) * 100
                if diff_percent > 10:
                    self.logger.warning(
                        f"Suma de fuentes ({sources_sum:.0f}) vs total ({total:.0f}): {diff_percent:.1f}%"
                    )
                    # No fallar — CENACE puede incluir/excluir exportación en el total

            return True

        except Exception as e:
            self.logger.error(f"Error validando datos: {e}")
            return False

    # ======================================================================
    # MÉTODOS PRIVADOS
    # ======================================================================

    def _extract_resumen_boxes(self, container) -> Dict:
        """
        Lee todos los <div class="resumen-box [clase]"> dentro de un contenedor.
        Usa la clase CSS para identificar qué dato es cada caja.
        """
        data = {}
        boxes = container.find_all('div', class_='resumen-box')

        for box in boxes:
            # Obtener clases del div (ej: ['resumen-box', 'total'])
            classes = box.get('class', [])
            divs = box.find_all('div', recursive=False)
            if len(divs) < 2:
                continue

            value_text = divs[1].get_text(strip=True)
            value = parse_cenace_number(value_text)

            if value is None:
                continue

            # Mapear por clase CSS (más confiable que el texto del label)
            if 'total' in classes:
                data['total_mwh'] = value
            elif 'hidraulica' in classes:
                data['hydro_mwh'] = value
            elif 'otra' in classes:
                data['thermal_mwh'] = value
            elif 'noconvencional' in classes:
                data['renewable_mwh'] = value
            elif 'exportacion' in classes:
                data['export_mwh'] = value
            elif 'importacion' in classes:
                data['import_mwh'] = value
            elif 'anterior' in classes:
                data['demand_previous_mw'] = value

        # Valores por defecto si faltan
        data.setdefault('import_mwh', 0.0)
        data.setdefault('export_mwh', 0.0)
        return data

    def _extract_plants_from_plotly_script(self, script_text: str) -> List[Dict]:
        """
        Extrae datos de centrales desde el JSON de Plotly.newPlot().
        Los gráficos de barras tienen: name=central, y=[valor_mwh], type='bar'
        """
        plants = []
        try:
            # Extraer el JSON de datos del primer argumento de Plotly.newPlot(id, DATA, layout)
            match = re.search(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\]),\s*\{', script_text, re.DOTALL)
            if not match:
                return []

            traces_json = match.group(1)
            traces = json.loads(traces_json)

            for trace in traces:
                if trace.get('type') != 'bar':
                    continue
                name = trace.get('name', '')
                y_data = trace.get('y', [])

                # y puede ser lista simple o dict con dtype/bdata (binario base64)
                if isinstance(y_data, dict) and y_data.get('dtype') == 'f8':
                    import base64
                    raw = base64.b64decode(y_data['bdata'])
                    count = len(raw) // 8
                    values = list(struct.unpack(f'{count}d', raw))
                    mwh = values[0] if values else 0
                elif isinstance(y_data, list) and y_data:
                    mwh = float(y_data[0]) if y_data[0] is not None else 0
                else:
                    continue

                if name and mwh > 0:
                    plants.append({
                        'plant_id': self._to_plant_id(name),
                        'plant_name': name,
                        'mwh': round(mwh, 2),
                        'plant_type': self._infer_plant_type(name),
                        'percentage': 0,
                    })

        except Exception as e:
            self.logger.debug(f"Error extrayendo plantas de Plotly: {e}")

        return plants

    def _extract_hourly_from_plotly_script(self, script_text: str) -> List[Dict]:
        """
        Extrae la curva horaria del gráfico Plotly de área apilada.
        Retorna lista de dicts con hora y valores por tipo.
        """
        hourly = []
        try:
            match = re.search(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\]),\s*\{', script_text, re.DOTALL)
            if not match:
                return []

            traces = json.loads(match.group(1))

            # Encontrar las series por nombre
            series = {}
            x_labels = []
            for trace in traces:
                name = trace.get('name', '')
                x = trace.get('x', [])
                if x and not x_labels:
                    x_labels = x

                y_data = trace.get('y', [])
                if isinstance(y_data, dict) and y_data.get('dtype') == 'f8':
                    import base64
                    raw = base64.b64decode(y_data['bdata'])
                    count = len(raw) // 8
                    values = list(struct.unpack(f'{count}d', raw))
                    # Reemplazar NaN/inf por 0
                    values = [v if (v == v and abs(v) < 1e15) else 0 for v in values]
                    series[name] = values
                elif isinstance(y_data, list):
                    series[name] = [float(v) if v is not None else 0 for v in y_data]

            today = datetime.now().date()
            for i, label in enumerate(x_labels):
                try:
                    hour_str = label  # "00:00", "00:30", etc.
                    h, m = map(int, hour_str.split(':'))
                    hourly.append({
                        'date': today,
                        'hour': h,
                        'minute': m,
                        'hydro_mw': series.get('Hidráulica', [0]*len(x_labels))[i],
                        'thermal_mw': series.get('Térmica', [0]*len(x_labels))[i],
                        'renewable_mw': series.get('Renovable', [0]*len(x_labels))[i],
                        'import_mw': series.get('Importación', [0]*len(x_labels))[i],
                        'export_mw': series.get('Exportación', [0]*len(x_labels))[i],
                        'total_production_mw': series.get('PRODUCCIÓN TOTAL', [0]*len(x_labels))[i],
                        'demand_mw': series.get('DEMANDA NACIONAL', [0]*len(x_labels))[i],
                    })
                except Exception:
                    continue

        except Exception as e:
            self.logger.debug(f"Error extrayendo curva horaria: {e}")

        return hourly

    def _infer_plant_type(self, plant_name: str) -> str:
        """Infiere tipo de central basado en el nombre"""
        name_normalized = normalize_text(plant_name)

        if any(w in name_normalized for w in ['hidro', 'hydro', 'presa', 'mazar', 'coca', 'paute',
                                                'sopladora', 'agoy', 'delsitanisagua', 'francisco',
                                                'salto', 'embalse', 'otras hidro']):
            return 'HYDRO'
        elif any(w in name_normalized for w in ['termica', 'termico', 'thermal', 'carbon',
                                                  'gas', 'fuel', 'termo', 'gas natural']):
            return 'THERMAL'
        elif any(w in name_normalized for w in ['eolica', 'eolico', 'wind', 'solar',
                                                  'fotovoltaica', 'biomasa', 'renovable']):
            return 'RENEWABLE'
        else:
            return 'OTHER'

    def _to_plant_id(self, plant_name: str) -> str:
        """Convierte el nombre de una central en un identificador estable."""
        normalized = normalize_text(plant_name)
        compact = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        return compact.upper() if compact else "UNKNOWN"