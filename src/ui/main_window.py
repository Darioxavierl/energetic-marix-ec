"""
Ventana principal de la aplicación PyQt6
"""
import json
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QFrame,
    QSplitter,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QFormLayout,
)
from PyQt6.QtCore import Qt, QTimer

from src.application.scenario_manager import ScenarioManager
from src.application.simulation_controller import SimulationController
from src.application.plant_generation_mapper import (
    calculate_plant_utilization,
    map_live_generation_to_centrales,
)
from src.domain.models.simulation_state import DataSourceMode, SimulationState
from src.domain.simulation.generation_allocator import (
    calculate_utilization_by_type,
    split_renewable_generation,
)
from src.infrastructure.api.cenace_client import CENACEClient
from src.infrastructure.events.event_bus import EventBus
from src.ui.map_widget import MapWidget
from config.settings import (
    APP_TITLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    CENTRALES_JSON,
    MICROSERVICE_BASE_URL,
    MICROSERVICE_TIMEOUT_SECONDS,
    MICROSERVICE_SYNC_INTERVAL_MS,
    SCENARIOS_DIR,
)


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    def __init__(self):
        super().__init__()
        self.centrales = []
        self.central_lookup: dict[str, dict] = {}
        self.selected_central_id: str | None = None
        self.installed_by_type_mw = {"HYDRO": 0.0, "THERMAL": 0.0, "WIND": 0.0, "SOLAR": 0.0}
        self.installed_by_id_mw: dict[str, float] = {}
        self._build_services()
        self._setup_ui()
        self._setup_sync_timer()

    def _build_services(self) -> None:
        """Create service adapters and controller dependencies."""
        self.cenace_client = CENACEClient(
            base_url=MICROSERVICE_BASE_URL,
            timeout_seconds=MICROSERVICE_TIMEOUT_SECONDS,
        )
        self.event_bus = EventBus()
        self.simulation_controller = SimulationController(self.cenace_client)
        self.scenario_manager = ScenarioManager(SCENARIOS_DIR)

        self.event_bus.subscribe("state_updated", self._on_state_updated)
        self.event_bus.subscribe("sync_error", self._on_sync_error)

    def _setup_ui(self) -> None:
        """Configura la interfaz de usuario"""
        # Propiedades de la ventana
        self.setWindowTitle(APP_TITLE)
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)

        # Widget central con layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Crear y agregar panel de simulacion
        control_panel = self._build_control_panel()
        splitter.addWidget(control_panel)

        # Crear y agregar widget del mapa
        self.map_widget = MapWidget()
        splitter.addWidget(self.map_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, max(WINDOW_WIDTH - 320, 600)])

        layout.addWidget(splitter)

        # Cargar datos al estar listo el mapa
        self.map_widget.bridge.map_ready_event.connect(self._on_map_ready)
        self.map_widget.bridge.marker_clicked_event.connect(self._on_map_marker_clicked)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Mostrar mensaje de inicio
        print(f"✓ {APP_TITLE} iniciada")

    def _build_control_panel(self) -> QWidget:
        """Build left panel with controls and live KPIs."""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(360)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Control de Simulacion")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        self.mode_label = QLabel("Modo: AUTOMATIC")
        layout.addWidget(self.mode_label)

        self.status_label = QLabel("Estado: Esperando sincronizacion")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        central_title = QLabel("Detalle de Central")
        central_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        layout.addWidget(central_title)

        self.central_selector = QComboBox()
        self.central_selector.currentTextChanged.connect(self._on_central_selected)
        layout.addWidget(self.central_selector)

        central_form = QFormLayout()
        self.central_type_label = QLabel("-")
        central_form.addRow("Tipo", self.central_type_label)

        self.central_region_label = QLabel("-")
        central_form.addRow("Region", self.central_region_label)

        self.central_installed_label = QLabel("-")
        central_form.addRow("Instalada MW", self.central_installed_label)

        self.central_available_spin = QDoubleSpinBox()
        self.central_available_spin.setRange(0.0, 5000.0)
        self.central_available_spin.setSingleStep(5.0)
        self.central_available_spin.setEnabled(False)
        central_form.addRow("Disponible MW", self.central_available_spin)

        self.central_status_combo = QComboBox()
        self.central_status_combo.addItems(["ONLINE", "OFFLINE", "MAINTENANCE"])
        self.central_status_combo.setEnabled(False)
        central_form.addRow("Estado", self.central_status_combo)
        layout.addLayout(central_form)

        self.apply_central_button = QPushButton("Aplicar central")
        self.apply_central_button.setEnabled(False)
        self.apply_central_button.clicked.connect(self._apply_central_edit)
        layout.addWidget(self.apply_central_button)

        scenario_title = QLabel("Escenarios")
        scenario_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        layout.addWidget(scenario_title)

        self.scenario_name_input = QLineEdit()
        self.scenario_name_input.setPlaceholderText("Nombre de escenario")
        layout.addWidget(self.scenario_name_input)

        self.scenario_selector = QComboBox()
        layout.addWidget(self.scenario_selector)

        scenario_buttons = QHBoxLayout()
        self.save_scenario_button = QPushButton("Guardar")
        self.save_scenario_button.clicked.connect(self._save_scenario)
        scenario_buttons.addWidget(self.save_scenario_button)

        self.load_scenario_button = QPushButton("Restaurar")
        self.load_scenario_button.clicked.connect(self._load_selected_scenario)
        scenario_buttons.addWidget(self.load_scenario_button)
        layout.addLayout(scenario_buttons)

        scenario_buttons_2 = QHBoxLayout()
        self.duplicate_scenario_button = QPushButton("Duplicar")
        self.duplicate_scenario_button.clicked.connect(self._duplicate_selected_scenario)
        scenario_buttons_2.addWidget(self.duplicate_scenario_button)

        self.delete_scenario_button = QPushButton("Descartar")
        self.delete_scenario_button.clicked.connect(self._delete_selected_scenario)
        scenario_buttons_2.addWidget(self.delete_scenario_button)
        layout.addLayout(scenario_buttons_2)

        button_row = QHBoxLayout()
        self.sync_button = QPushButton("Sincronizar ahora")
        self.sync_button.clicked.connect(self._sync_now)
        button_row.addWidget(self.sync_button)

        self.mode_button = QPushButton("Cambiar a MANUAL")
        self.mode_button.clicked.connect(self._toggle_mode)
        button_row.addWidget(self.mode_button)
        layout.addLayout(button_row)

        self.delta_input = QDoubleSpinBox()
        self.delta_input.setRange(-50.0, 50.0)
        self.delta_input.setSingleStep(1.0)
        self.delta_input.setSuffix(" % demanda")
        self.delta_input.setValue(0.0)
        self.delta_input.setEnabled(False)
        layout.addWidget(self.delta_input)

        self.apply_manual_button = QPushButton("Aplicar ajuste manual")
        self.apply_manual_button.setEnabled(False)
        self.apply_manual_button.clicked.connect(self._apply_manual_adjustment)
        layout.addWidget(self.apply_manual_button)

        self.metrics_label = QLabel(self._format_metrics(self.simulation_controller.state))
        self.metrics_label.setStyleSheet("font-family: Consolas; font-size: 12px;")
        self.metrics_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.metrics_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.metrics_label)

        layout.addStretch(1)
        panel.setLayout(layout)
        self._refresh_scenario_selector()
        return panel

    def _setup_sync_timer(self) -> None:
        """Refresh automatic values at a fixed interval."""
        self.sync_timer = QTimer(self)
        self.sync_timer.setInterval(MICROSERVICE_SYNC_INTERVAL_MS)
        self.sync_timer.timeout.connect(self._sync_now)
        self.sync_timer.start()

    def _on_map_ready(self):
        """Manejador para cuando el mapa está listo para recibir instrucciones de PyQt"""
        print("✓ Mapa listo, cargando centrales...")
        try:
            with open(CENTRALES_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                centrales = data.get("data", {}).get("centrales", [])
                self.centrales = centrales
                self.central_lookup = {str(c.get("id")): c for c in centrales}
                self._rebuild_installed_by_type()
                self._refresh_central_selector()
                self.map_widget.add_centrales(centrales)
                print(f"✓ {len(centrales)} centrales cargadas")
        except Exception as e:
            print(f"Error cargando centrales: {e}")

        # Primer pull al estar listo el UI + mapa
        self._sync_now()

    def _sync_now(self) -> None:
        """Trigger a safe sync from microservice and update panel."""
        state, error = self.simulation_controller.safe_sync()
        if error:
            self.event_bus.publish("sync_error", {"error": error})
        else:
            self.event_bus.publish("state_updated", {"state": state, "origin": "sync"})

    def _toggle_mode(self) -> None:
        """Switch between automatic and manual mode."""
        new_mode = (
            DataSourceMode.MANUAL
            if self.simulation_controller.state.mode == DataSourceMode.AUTOMATIC
            else DataSourceMode.AUTOMATIC
        )
        state = self.simulation_controller.switch_mode(new_mode)
        self.event_bus.publish("state_updated", {"state": state, "origin": "mode_switch"})

    def _apply_manual_adjustment(self) -> None:
        """Apply demand percentage delta while in manual mode."""
        delta = self.delta_input.value()
        state = self.simulation_controller.apply_manual_demand_delta(delta)
        self.event_bus.publish("state_updated", {"state": state, "origin": "manual_adjust"})

    def _on_state_updated(self, payload: dict) -> None:
        """Handle state updates emitted through internal event bus."""

        state = payload.get("state", self.simulation_controller.state)
        source_ts = state.source_timestamp.isoformat(sep=" ", timespec="seconds") if state.source_timestamp else "N/A"
        self.status_label.setText(f"Estado: Datos activos. Fuente: {source_ts}")
        self._render_state(state)

    def _on_sync_error(self, payload: dict) -> None:
        """Handle sync errors emitted through internal event bus."""

        error = payload.get("error", "Error desconocido")
        self.status_label.setText(f"Estado: Error de conexion. {error}")

    def _refresh_scenario_selector(self) -> None:
        """Reload scenario names from persistent storage into combo box."""

        current = self.scenario_selector.currentText()
        names = self.scenario_manager.list_scenarios()
        self.scenario_selector.clear()
        self.scenario_selector.addItems(names)
        if current and current in names:
            self.scenario_selector.setCurrentText(current)

    def _save_scenario(self) -> None:
        """Persist current state as named scenario."""

        raw_name = self.scenario_name_input.text().strip() or self.scenario_selector.currentText().strip()
        if not raw_name:
            QMessageBox.warning(self, "Escenario", "Ingrese un nombre para guardar el escenario.")
            return

        state = self.simulation_controller.get_state_snapshot()
        target = self.scenario_manager.save(raw_name, state)
        self._refresh_scenario_selector()
        self.scenario_selector.setCurrentText(target.stem)
        self.status_label.setText(f"Estado: Escenario guardado ({target.stem}).")

    def _load_selected_scenario(self) -> None:
        """Load selected scenario into current simulation session."""

        name = self.scenario_selector.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Escenario", "Seleccione un escenario para restaurar.")
            return

        try:
            loaded = self.scenario_manager.load(name)
            state = self.simulation_controller.set_state(loaded)
            self.event_bus.publish("state_updated", {"state": state, "origin": "scenario_load"})
            self.status_label.setText(f"Estado: Escenario restaurado ({name}).")
        except FileNotFoundError as exc:
            QMessageBox.critical(self, "Escenario", str(exc))

    def _duplicate_selected_scenario(self) -> None:
        """Duplicate currently selected scenario with a new derived name."""

        source_name = self.scenario_selector.currentText().strip()
        if not source_name:
            QMessageBox.warning(self, "Escenario", "Seleccione un escenario para duplicar.")
            return

        new_name = f"{source_name}_copy"
        target = self.scenario_manager.duplicate(source_name, new_name)
        self._refresh_scenario_selector()
        self.scenario_selector.setCurrentText(target.stem)
        self.status_label.setText(f"Estado: Escenario duplicado ({target.stem}).")

    def _delete_selected_scenario(self) -> None:
        """Delete currently selected scenario file from local storage."""

        name = self.scenario_selector.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Escenario", "Seleccione un escenario para descartar.")
            return

        self.scenario_manager.delete(name)
        self._refresh_scenario_selector()
        self.status_label.setText(f"Estado: Escenario descartado ({name}).")

    def _render_state(self, state: SimulationState) -> None:
        """Push current state values to UI elements."""
        is_manual = state.mode == DataSourceMode.MANUAL
        self.mode_label.setText(f"Modo: {state.mode.value}")
        self.mode_button.setText("Cambiar a AUTOMATIC" if is_manual else "Cambiar a MANUAL")
        self.delta_input.setEnabled(is_manual)
        self.apply_manual_button.setEnabled(is_manual)
        self.central_available_spin.setEnabled(is_manual)
        self.central_status_combo.setEnabled(is_manual)
        self.apply_central_button.setEnabled(is_manual and self.selected_central_id is not None)
        self.metrics_label.setText(self._format_metrics(state))
        self._update_map_overlay(state)

    def _rebuild_installed_by_type(self) -> None:
        """Aggregate installed capacities from static central catalog."""
        totals = {"HYDRO": 0.0, "THERMAL": 0.0, "WIND": 0.0, "SOLAR": 0.0}
        by_id: dict[str, float] = {}
        for central in self.centrales:
            central_id = str(central.get("id", ""))
            plant_type = str(central.get("type", "")).upper()
            installed = float(central.get("installed_capacity_mw", 0.0) or 0.0)
            by_id[central_id] = max(0.0, installed)
            if plant_type in totals:
                totals[plant_type] += max(0.0, installed)
        self.installed_by_type_mw = totals
        self.installed_by_id_mw = by_id

    def _update_map_overlay(self, state: SimulationState) -> None:
        """Project current simulation state to technology intensity on map markers."""
        if not self.centrales:
            return

        renewable_split = split_renewable_generation(
            renewable_mw=state.renewable_mw,
            wind_capacity_mw=self.installed_by_type_mw.get("WIND", 0.0),
            solar_capacity_mw=self.installed_by_type_mw.get("SOLAR", 0.0),
        )
        generation_by_type_mw = {
            "HYDRO": max(0.0, state.hydro_mw),
            "THERMAL": max(0.0, state.thermal_mw),
            "WIND": renewable_split.get("WIND", 0.0),
            "SOLAR": renewable_split.get("SOLAR", 0.0),
        }
        utilization_by_type = calculate_utilization_by_type(
            generation_by_type_mw=generation_by_type_mw,
            installed_by_type_mw=self.installed_by_type_mw,
        )

        live_plants = self.simulation_controller.get_latest_plants_snapshot()
        generation_by_plant_id_mw = map_live_generation_to_centrales(self.centrales, live_plants)
        utilization_by_plant_id = calculate_plant_utilization(
            generation_by_id_mw=generation_by_plant_id_mw,
            installed_by_id_mw=self.installed_by_id_mw,
        )

        self.map_widget.update_generation_overlay(
            generation_by_type_mw,
            utilization_by_type,
            generation_by_plant_id_mw=generation_by_plant_id_mw,
            utilization_by_plant_id=utilization_by_plant_id,
        )

    def _refresh_central_selector(self) -> None:
        """Populate central selector with current catalog entries."""

        current = self.selected_central_id
        items = sorted(self.centrales, key=lambda x: str(x.get("name", "")))
        self.central_selector.clear()
        for central in items:
            cid = str(central.get("id", ""))
            name = str(central.get("name", cid))
            self.central_selector.addItem(f"{name} | {cid}", cid)

        if current:
            index = self.central_selector.findData(current)
            if index >= 0:
                self.central_selector.setCurrentIndex(index)
                return

        if self.central_selector.count() > 0:
            self.central_selector.setCurrentIndex(0)

    def _on_map_marker_clicked(self, marker_id: str, lat: float, lon: float) -> None:
        """Sync map marker selection into central detail panel."""

        del lat, lon
        index = self.central_selector.findData(marker_id)
        if index >= 0:
            self.central_selector.setCurrentIndex(index)

    def _on_central_selected(self, _label: str) -> None:
        """Sync combo selection into internal state and map focus."""

        central_id = self.central_selector.currentData()
        self.selected_central_id = str(central_id) if central_id else None
        self._render_selected_central()
        if self.selected_central_id:
            self.map_widget.focus_marker(self.selected_central_id)

    def _render_selected_central(self) -> None:
        """Render selected central information in detail controls."""

        if not self.selected_central_id:
            self.central_type_label.setText("-")
            self.central_region_label.setText("-")
            self.central_installed_label.setText("-")
            self.central_available_spin.setValue(0.0)
            return

        central = self.central_lookup.get(self.selected_central_id)
        if not central:
            return

        self.central_type_label.setText(str(central.get("type", "-")))
        self.central_region_label.setText(str(central.get("region", "-")))
        installed = float(central.get("installed_capacity_mw", 0.0) or 0.0)
        available = float(central.get("available_capacity_mw", 0.0) or 0.0)
        status = str(central.get("status", "ONLINE"))

        self.central_installed_label.setText(f"{installed:.2f}")
        self.central_available_spin.setValue(available)
        status_index = self.central_status_combo.findText(status)
        self.central_status_combo.setCurrentIndex(status_index if status_index >= 0 else 0)

    def _apply_central_edit(self) -> None:
        """Apply selected central edits while in manual mode."""

        if self.simulation_controller.state.mode != DataSourceMode.MANUAL:
            return
        if not self.selected_central_id:
            return

        central = self.central_lookup.get(self.selected_central_id)
        if not central:
            return

        central["available_capacity_mw"] = float(self.central_available_spin.value())
        central["status"] = str(self.central_status_combo.currentText())
        self._rebuild_installed_by_type()
        self._update_map_overlay(self.simulation_controller.state)
        self.status_label.setText(f"Estado: Central actualizada ({self.selected_central_id}).")

    @staticmethod
    def _format_metrics(state: SimulationState) -> str:
        """Return KPI summary text."""
        return (
            "KPI sistema\n"
            f"Demanda MW:         {state.demand_mw:10.2f}\n"
            f"Hidro MW:           {state.hydro_mw:10.2f}\n"
            f"Termica MW:         {state.thermal_mw:10.2f}\n"
            f"Renovable MW:       {state.renewable_mw:10.2f}\n"
            f"Import MW:          {state.import_mw:10.2f}\n"
            f"Export MW:          {state.export_mw:10.2f}\n"
            "--------------------------------\n"
            f"Oferta total MW:    {state.metrics.total_supply_mw:10.2f}\n"
            f"Balance MW:         {state.metrics.balance_mw:10.2f}\n"
            f"Reserva %:          {state.metrics.reserve_margin_pct:10.2f}\n"
            f"Riesgo:             {state.metrics.risk_level}"
        )

