"""
Ventana principal de la aplicación PyQt6
"""
import copy
import json
import logging
from datetime import datetime
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
    QSlider,
)
from PyQt6.QtCore import Qt, QTimer

from src.application.scenario_manager import ScenarioManager
from src.application.simulation_controller import SimulationController
from src.application.manual_catalog_baseline import (
    calculate_manual_residual_by_type,
    build_manual_catalog_from_automatic_state_with_diagnostics,
    build_manual_catalog_from_live_with_diagnostics,
    has_usable_live_snapshot,
    is_snapshot_timestamp_fresh,
    neutralize_hydro_reservoir_for_entry,
    normalize_hydro_contract,
)
from src.application.plant_generation_mapper import (
    calculate_plant_utilization,
    map_live_generation_to_centrales,
)
from src.domain.models.simulation_state import DataSourceMode, SimulationState
from src.domain.simulation.generation_allocator import (
    calculate_utilization_by_type,
    split_renewable_generation,
)
from src.domain.simulation.generation_aggregator import (
    aggregate_generation_by_plant,
    aggregate_generation_by_type,
)
from src.infrastructure.api.cenace_client import CENACEClient
from src.infrastructure.events.event_bus import EventBus
from src.ui.charts_data_mapper import (
    append_history_point,
    build_charts_payload,
    build_history_point_with_origin,
)
from src.ui.charts_widget import ChartsWidget
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
    HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT,
    GLOBAL_DROUGHT_DEFAULT,
    GLOBAL_DROUGHT_MIN,
    GLOBAL_DROUGHT_MAX,
    CHART_HISTORY_MAX_POINTS,
    MANUAL_BASELINE_SNAPSHOT_MAX_AGE_MINUTES,
    MANUAL_ENTRY_HYDRO_NEUTRALIZE_ON_SWITCH,
    MANUAL_ENTRY_HYDRO_NEUTRAL_RESERVOIR_PCT,
    MODE_SWITCH_DIAGNOSTICS_ENABLED,
)


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    def __init__(self):
        super().__init__()
        self.centrales = []
        self.base_centrales: list[dict] = []
        self.central_lookup: dict[str, dict] = {}
        self.selected_central_id: str | None = None
        self.global_drought_pct: float = GLOBAL_DROUGHT_DEFAULT
        self.installed_by_type_mw = {"HYDRO": 0.0, "THERMAL": 0.0, "WIND": 0.0, "SOLAR": 0.0}
        self.installed_by_id_mw: dict[str, float] = {}
        self.chart_history: list[dict] = []
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

        # Crear layout derecho con mapa + panel de graficas
        right_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.map_widget = MapWidget()
        self.charts_widget = ChartsWidget()
        self.charts_widget.setMinimumWidth(360)
        self.charts_widget.setMaximumWidth(540)
        right_splitter.addWidget(self.map_widget)
        right_splitter.addWidget(self.charts_widget)
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 0)
        right_splitter.setSizes([max(WINDOW_WIDTH - 760, 600), 420])
        splitter.addWidget(right_splitter)
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

        self.hydro_reservoir_spin = QDoubleSpinBox()
        self.hydro_reservoir_spin.setRange(0.0, 100.0)
        self.hydro_reservoir_spin.setSingleStep(5.0)
        self.hydro_reservoir_spin.setSuffix(" %")
        self.hydro_reservoir_spin.setEnabled(False)
        self.hydro_reservoir_spin.setToolTip(
            "Factor hídrico [0–100%] aplicado sobre la capacidad disponible.\n"
            "100% = sin restricción hídrica (turbina a plena potencia declarada).\n"
            "No representa el nivel físico del embalse en metros o hm³."
        )
        central_form.addRow("Disp. hídrica %", self.hydro_reservoir_spin)

        layout.addLayout(central_form)

        global_drought_row = QHBoxLayout()
        self.global_drought_label = QLabel("Sequia global: 0%")
        global_drought_row.addWidget(self.global_drought_label)
        layout.addLayout(global_drought_row)

        self.global_drought_slider = QSlider(Qt.Orientation.Horizontal)
        self.global_drought_slider.setMinimum(int(GLOBAL_DROUGHT_MIN))
        self.global_drought_slider.setMaximum(int(GLOBAL_DROUGHT_MAX))
        self.global_drought_slider.setValue(int(GLOBAL_DROUGHT_DEFAULT))
        self.global_drought_slider.setEnabled(False)
        self.global_drought_slider.valueChanged.connect(self._on_global_drought_changed)
        layout.addWidget(self.global_drought_slider)

        self.apply_central_button = QPushButton("Aplicar central")
        self.apply_central_button.setEnabled(False)
        self.apply_central_button.clicked.connect(self._apply_central_edit)
        layout.addWidget(self.apply_central_button)

        interconnection_title = QLabel("Interconexión")
        interconnection_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        layout.addWidget(interconnection_title)

        interconnection_form = QFormLayout()
        self.import_spin = QDoubleSpinBox()
        self.import_spin.setRange(0.0, 500.0)
        self.import_spin.setSingleStep(10.0)
        self.import_spin.setSuffix(" MW")
        self.import_spin.setEnabled(False)
        self.import_spin.setToolTip("Energía importada desde redes vecinas (Colombia / Perú).")
        interconnection_form.addRow("Importación MW", self.import_spin)

        self.export_spin = QDoubleSpinBox()
        self.export_spin.setRange(0.0, 500.0)
        self.export_spin.setSingleStep(10.0)
        self.export_spin.setSuffix(" MW")
        self.export_spin.setEnabled(False)
        self.export_spin.setToolTip("Energía exportada hacia redes vecinas (Colombia / Perú).")
        interconnection_form.addRow("Exportación MW", self.export_spin)
        layout.addLayout(interconnection_form)

        self.import_spin.valueChanged.connect(self._on_interconnection_changed)
        self.export_spin.valueChanged.connect(self._on_interconnection_changed)

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

        self.reset_manual_button = QPushButton("Reset MANUAL")
        self.reset_manual_button.setEnabled(False)
        self.reset_manual_button.clicked.connect(self._reset_manual_baseline)
        button_row.addWidget(self.reset_manual_button)
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
                centrales = normalize_hydro_contract(data.get("data", {}).get("centrales", []))
                self.centrales = centrales
                self.base_centrales = copy.deepcopy(centrales)
                self.central_lookup = {str(c.get("id")): c for c in centrales}
                self.chart_history.clear()
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
        pre_state = self.simulation_controller.get_state_snapshot()
        new_mode = (
            DataSourceMode.MANUAL
            if self.simulation_controller.state.mode == DataSourceMode.AUTOMATIC
            else DataSourceMode.AUTOMATIC
        )
        state = self.simulation_controller.switch_mode(new_mode)
        baseline_source = ""
        baseline_diagnostics: dict = {}
        if new_mode == DataSourceMode.MANUAL and self.centrales:
            self.centrales, baseline_source, baseline_diagnostics = self._build_manual_entry_catalog(pre_state)
            self.global_drought_pct = GLOBAL_DROUGHT_DEFAULT
            if MANUAL_ENTRY_HYDRO_NEUTRALIZE_ON_SWITCH:
                neutralization = neutralize_hydro_reservoir_for_entry(
                    self.centrales,
                    target_reservoir_pct=MANUAL_ENTRY_HYDRO_NEUTRAL_RESERVOIR_PCT,
                )
                baseline_diagnostics = {**baseline_diagnostics, **neutralization}
            residual_diagnostics = calculate_manual_residual_by_type(
                pre_state,
                self.centrales,
                global_drought_factor=(self.global_drought_pct / 100.0),
            )
            baseline_diagnostics = {**baseline_diagnostics, **residual_diagnostics}
            self.central_lookup = {str(c.get("id")): c for c in self.centrales}
            self._rebuild_installed_by_type()
            self._refresh_central_selector()
            self.simulation_controller.set_manual_residual_by_type(
                residual_diagnostics.get("residual_by_type_mw", {}),
                baseline_source=baseline_source,
                residual_reason="catalog_gap_or_non_catalogued_generation",
            )
            state = self.simulation_controller.apply_manual_central_catalog(
                self.centrales,
                global_drought_factor=(self.global_drought_pct / 100.0),
                import_mw=pre_state.import_mw,
                export_mw=pre_state.export_mw,
            )
        elif new_mode == DataSourceMode.AUTOMATIC:
            self.global_drought_pct = GLOBAL_DROUGHT_DEFAULT
        self.event_bus.publish("state_updated", {"state": state, "origin": "mode_switch"})
        if baseline_source:
            self.status_label.setText(f"Estado: MANUAL inicializado desde {baseline_source}.")
        if MODE_SWITCH_DIAGNOSTICS_ENABLED and new_mode == DataSourceMode.MANUAL:
            self._log_mode_switch_diagnostics(pre_state, state, baseline_source, baseline_diagnostics)

    def _build_manual_entry_catalog(self, pre_state: SimulationState) -> tuple[list[dict], str, dict]:
        """Build MANUAL baseline from latest live plants when available, else JSON baseline."""

        live_plants = self.simulation_controller.get_latest_plants_snapshot()
        is_fresh = is_snapshot_timestamp_fresh(
            pre_state.source_timestamp,
            MANUAL_BASELINE_SNAPSHOT_MAX_AGE_MINUTES,
            now=datetime.now(),
        )

        if self.base_centrales and has_usable_live_snapshot(live_plants) and is_fresh:
            baseline, diagnostics = build_manual_catalog_from_live_with_diagnostics(
                self.base_centrales,
                live_plants,
            )
            diagnostics["fallback_reason"] = "none"
            return baseline, "snapshot live", diagnostics

        if self.base_centrales and pre_state.mode == DataSourceMode.AUTOMATIC:
            baseline, diagnostics = build_manual_catalog_from_automatic_state_with_diagnostics(
                self.base_centrales,
                pre_state,
            )
            if not has_usable_live_snapshot(live_plants):
                diagnostics["fallback_reason"] = "snapshot_live_unavailable"
            elif not is_fresh:
                diagnostics["fallback_reason"] = "snapshot_live_stale"
            else:
                diagnostics["fallback_reason"] = "snapshot_live_incompatible"
            return baseline, "estado agregado automatico", diagnostics

        if self.base_centrales and has_usable_live_snapshot(live_plants):
            baseline, diagnostics = build_manual_catalog_from_live_with_diagnostics(
                self.base_centrales,
                live_plants,
            )
            diagnostics["fallback_reason"] = "automatic_state_unavailable"
            return baseline, "snapshot live", diagnostics
        return copy.deepcopy(self.base_centrales), "JSON base (fallback)", {"fallback_reason": "no_live_or_automatic"}

    def _log_mode_switch_diagnostics(
        self,
        pre_state: SimulationState,
        post_state: SimulationState,
        baseline_source: str,
        baseline_diagnostics: dict,
    ) -> None:
        """Emit diagnostic summary for AUTOMATIC -> MANUAL transition discrepancies."""

        delta_hydro = float(post_state.hydro_mw - pre_state.hydro_mw)
        delta_thermal = float(post_state.thermal_mw - pre_state.thermal_mw)
        delta_renewable = float(post_state.renewable_mw - pre_state.renewable_mw)
        delta_supply = float(post_state.metrics.total_supply_mw - pre_state.metrics.total_supply_mw)
        delta_reserve = float(post_state.metrics.reserve_margin_pct - pre_state.metrics.reserve_margin_pct)

        causes: list[str] = []
        hydro_drop = pre_state.hydro_mw > 0.0 and post_state.hydro_mw < (pre_state.hydro_mw * 0.85)
        if hydro_drop:
            causes.append("hydro_factor_gap")

        renewable_drop = pre_state.renewable_mw > 0.0 and post_state.renewable_mw < (pre_state.renewable_mw * 0.7)
        unmatched = baseline_diagnostics.get("unmatched_pool_by_type", {})
        if renewable_drop and float(unmatched.get("RENEWABLE", 0.0) or 0.0) > 0.0:
            causes.append("renewable_type_mapping_gap")

        unallocated = baseline_diagnostics.get("unallocated_by_type_mw", {})
        unallocated_total = float(sum(float(v) for v in unallocated.values())) if isinstance(unallocated, dict) else 0.0
        if delta_supply < -200.0 and unallocated_total > 0.0:
            causes.append("catalog_capacity_gap")

        status_changes = baseline_diagnostics.get("status_changes", [])
        if len(status_changes) >= 5:
            causes.append("status_transition_gap")

        if baseline_diagnostics.get("hydro_entry_neutralized") is True:
            causes.append("hydro_entry_neutralized")

        fallback_reason = str(baseline_diagnostics.get("fallback_reason", "none"))

        logger.warning(
            "mode_switch_diagnostics source=%s pre={hydro:%.2f,thermal:%.2f,renewable:%.2f,supply:%.2f,reserve:%.2f} "
            "post={hydro:%.2f,thermal:%.2f,renewable:%.2f,supply:%.2f,reserve:%.2f} "
            "delta={hydro:%.2f,thermal:%.2f,renewable:%.2f,supply:%.2f,reserve:%.2f} causes=%s "
            "fallback_reason=%s baseline=%s",
            baseline_source,
            pre_state.hydro_mw,
            pre_state.thermal_mw,
            pre_state.renewable_mw,
            pre_state.metrics.total_supply_mw,
            pre_state.metrics.reserve_margin_pct,
            post_state.hydro_mw,
            post_state.thermal_mw,
            post_state.renewable_mw,
            post_state.metrics.total_supply_mw,
            post_state.metrics.reserve_margin_pct,
            delta_hydro,
            delta_thermal,
            delta_renewable,
            delta_supply,
            delta_reserve,
            causes or ["none"],
            fallback_reason,
            baseline_diagnostics,
        )

    def _reset_manual_baseline(self) -> None:
        """Reset current manual catalog and global drought to deterministic baseline."""

        if self.simulation_controller.state.mode != DataSourceMode.MANUAL:
            return

        self.centrales = copy.deepcopy(self.base_centrales)
        self.central_lookup = {str(c.get("id")): c for c in self.centrales}
        self._rebuild_installed_by_type()
        self._refresh_central_selector()
        self.global_drought_pct = GLOBAL_DROUGHT_DEFAULT
        self.simulation_controller.set_manual_residual_by_type({}, baseline_source="manual_reset", residual_reason="")
        state = self.simulation_controller.apply_manual_central_catalog(
            self.centrales,
            global_drought_factor=(self.global_drought_pct / 100.0),
        )
        self.event_bus.publish("state_updated", {"state": state, "origin": "manual_reset"})

    def _apply_manual_adjustment(self) -> None:
        """Apply demand percentage delta while in manual mode."""
        delta = self.delta_input.value()
        state = self.simulation_controller.apply_manual_demand_delta(delta)
        self.event_bus.publish("state_updated", {"state": state, "origin": "manual_adjust"})

    def _on_state_updated(self, payload: dict) -> None:
        """Handle state updates emitted through internal event bus."""

        state = payload.get("state", self.simulation_controller.state)
        origin = str(payload.get("origin", "state_updated"))
        source_ts = state.source_timestamp.isoformat(sep=" ", timespec="seconds") if state.source_timestamp else "N/A"
        self.status_label.setText(
            "Estado: Datos activos. "
            f"Fuente oficial: {source_ts} | "
            f"Oferta: {state.supply_source} | Demanda: {state.demand_source}"
        )
        append_history_point(
            self.chart_history,
            build_history_point_with_origin(state, origin),
            max_points=CHART_HISTORY_MAX_POINTS,
        )
        self._render_state(state)
        self._render_charts(state)

    def _on_sync_error(self, payload: dict) -> None:
        """Handle sync errors emitted through internal event bus."""

        error = payload.get("error", "Error desconocido")
        self.status_label.setText(f"Estado: Error de conexion. {error}")

    def _render_charts(self, state: SimulationState) -> None:
        """Render charts panel from current state and available timelines."""

        hourly_curve = self.simulation_controller.get_latest_hourly_curve_snapshot()
        payload = build_charts_payload(
            state=state,
            history=self.chart_history,
            hourly_curve=hourly_curve,
        )
        self.charts_widget.update_dashboard(payload)

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
        target = self.scenario_manager.save(raw_name, state, centrales=self.centrales)
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
            bundle = self.scenario_manager.load_bundle(name)
            loaded = bundle["state"]
            loaded_centrales = bundle.get("centrales")

            if loaded_centrales is not None:
                self.centrales = normalize_hydro_contract(loaded_centrales)
                self.central_lookup = {str(c.get("id")): c for c in self.centrales}
                self._rebuild_installed_by_type()
                self._refresh_central_selector()

            state = self.simulation_controller.set_state(loaded)
            if state.mode == DataSourceMode.MANUAL:
                state = self.simulation_controller.apply_manual_central_catalog(
                    self.centrales,
                    global_drought_factor=state.global_drought_factor,
                )
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
        self.global_drought_slider.setEnabled(is_manual)
        self.reset_manual_button.setEnabled(is_manual)
        self.hydro_reservoir_spin.setEnabled(is_manual and self.central_type_label.text().upper() == "HYDRO")
        self.apply_central_button.setEnabled(is_manual and self.selected_central_id is not None)
        self.import_spin.setEnabled(is_manual)
        self.export_spin.setEnabled(is_manual)
        self.global_drought_slider.blockSignals(True)
        self.global_drought_slider.setValue(int(round(state.global_drought_factor * 100.0)))
        self.global_drought_slider.blockSignals(False)
        self.global_drought_label.setText(
            f"Sequia global: {int(round(state.global_drought_factor * 100.0))}%"
        )
        self.import_spin.blockSignals(True)
        self.import_spin.setValue(state.import_mw)
        self.import_spin.blockSignals(False)
        self.export_spin.blockSignals(True)
        self.export_spin.setValue(state.export_mw)
        self.export_spin.blockSignals(False)
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
        if state.mode == DataSourceMode.MANUAL:
            generation_by_type_mw = aggregate_generation_by_type(
                self.centrales,
                global_drought_factor=state.global_drought_factor,
            )
            generation_by_plant_id_mw = aggregate_generation_by_plant(
                self.centrales,
                global_drought_factor=state.global_drought_factor,
            )
            utilization_by_type = calculate_utilization_by_type(
                generation_by_type_mw=generation_by_type_mw,
                installed_by_type_mw=self.installed_by_type_mw,
            )
            utilization_by_plant_id = calculate_plant_utilization(
                generation_by_id_mw=generation_by_plant_id_mw,
                installed_by_id_mw=self.installed_by_id_mw,
            )
        else:
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

        is_hydro = str(central.get("type", "")).upper() == "HYDRO"
        reservoir = float(central.get("reservoir_level_pct", HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT) or 0.0)

        self.hydro_reservoir_spin.setValue(reservoir)

        is_manual = self.simulation_controller.state.mode == DataSourceMode.MANUAL
        self.hydro_reservoir_spin.setEnabled(is_manual and is_hydro)

    def _on_global_drought_changed(self, value: int) -> None:
        """Apply global drought changes in manual mode and refresh KPIs immediately."""

        self.global_drought_pct = float(value)
        self.global_drought_label.setText(f"Sequia global: {value}%")
        if self.simulation_controller.state.mode != DataSourceMode.MANUAL:
            return

        state = self.simulation_controller.apply_manual_central_catalog(
            self.centrales,
            global_drought_factor=(self.global_drought_pct / 100.0),
        )
        self.event_bus.publish("state_updated", {"state": state, "origin": "global_drought"})

    def _on_interconnection_changed(self) -> None:
        """Apply import/export changes in manual mode and refresh KPIs immediately."""

        if self.simulation_controller.state.mode != DataSourceMode.MANUAL:
            return

        state = self.simulation_controller.apply_manual_interconnection(
            import_mw=self.import_spin.value(),
            export_mw=self.export_spin.value(),
        )
        self.event_bus.publish("state_updated", {"state": state, "origin": "interconnection"})

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
        if str(central.get("type", "")).upper() == "HYDRO":
            central["reservoir_level_pct"] = float(self.hydro_reservoir_spin.value())
        self._rebuild_installed_by_type()

        state = self.simulation_controller.apply_manual_central_catalog(
            self.centrales,
            global_drought_factor=(self.global_drought_pct / 100.0),
        )
        self.event_bus.publish("state_updated", {"state": state, "origin": "central_edit"})
        self.status_label.setText(f"Estado: Central actualizada ({self.selected_central_id}).")

    @staticmethod
    def _format_metrics(state: SimulationState) -> str:
        """Return KPI summary text."""
        window_note = ""
        if state.operational_window_hours > 1.0:
            window_note = f" (eq {state.operational_window_hours:.0f}h)"
        residual_total = (
            float(state.residual_hydro_mw)
            + float(state.residual_thermal_mw)
            + float(state.residual_renewable_mw)
        )

        return (
            "KPI sistema\n"
            "Operativo (MW)\n"
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
            f"Riesgo:             {state.metrics.risk_level}\n"
            f"Residual MW:        {residual_total:10.2f}\n"
            f"Residual H/T/R MW:  {state.residual_hydro_mw:6.2f} / {state.residual_thermal_mw:6.2f} / {state.residual_renewable_mw:6.2f}\n"
            "--------------------------------\n"
            "Resumen CENACE (MWh)\n"
            f"Total MWh:          {state.official_total_mwh:10.2f}\n"
            f"Hidro MWh:          {state.official_hydro_mwh:10.2f}\n"
            f"Termica MWh:        {state.official_thermal_mwh:10.2f}\n"
            f"Renovable MWh:      {state.official_renewable_mwh:10.2f}\n"
            f"Import MWh:         {state.official_import_mwh:10.2f}\n"
            f"Export MWh:         {state.official_export_mwh:10.2f}\n"
            "--------------------------------\n"
            f"Baseline MANUAL:    {state.manual_baseline_source or '-'}\n"
            f"Fuente demanda:     {state.demand_source}\n"
            f"Fuente oferta:      {state.supply_source}{window_note}\n"
            f"Residual motivo:    {state.manual_residual_reason or '-'}"
        )

