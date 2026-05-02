"""Web-based charts panel for dashboard analytics."""

from __future__ import annotations

import json

from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView


class ChartsWidget(QWebEngineView):
    """Renders operational charts using Chart.js in an embedded web view."""

    def __init__(self):
        super().__init__()
        self.setHtml(self._build_html(), QUrl("http://simulador-energetico-charts.local/"))

    def update_dashboard(self, payload: dict) -> None:
        """Push payload to web chart renderer."""

        payload_json = json.dumps(payload)
        self.page().runJavaScript(f"window.updateDashboard({payload_json});")

    @staticmethod
    def _build_html() -> str:
        """Return HTML document used for chart rendering."""

        return """
<!DOCTYPE html>
<html lang=\"es\">
<head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js\"></script>
    <style>
        * { box-sizing: border-box; }
        html, body {
            margin: 0;
            width: 100%;
            height: 100%;
            font-family: "Segoe UI", sans-serif;
            background: linear-gradient(180deg, #eef4fa 0%, #f8fbff 100%);
            color: #1f2937;
        }
        #root {
            height: 100%;
            overflow: auto;
            padding: 10px;
            display: grid;
            grid-template-columns: 1fr;
            gap: 10px;
        }
        .panel {
            background: #ffffff;
            border: 1px solid #dbe7f3;
            border-radius: 10px;
            padding: 8px 10px;
            box-shadow: 0 2px 10px rgba(17, 24, 39, 0.06);
        }
        .title {
            font-size: 12px;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 6px 0;
            display: flex;
            justify-content: space-between;
        }
        .meta {
            font-size: 11px;
            color: #475569;
        }
        .kpis {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }
        .kpi {
            border: 1px dashed #cbd5e1;
            border-radius: 8px;
            padding: 6px;
            background: #f8fafc;
        }
        .kpi-label { font-size: 10px; color: #64748b; }
        .kpi-value { font-size: 14px; font-weight: 700; color: #0f172a; }
        canvas { width: 100% !important; height: 170px !important; }
        #riskBadge {
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 700;
            color: white;
        }
    </style>
</head>
<body>
    <div id=\"root\">
        <div class=\"panel\">
            <div class=\"title\">Estado Operativo <span id=\"riskBadge\">UNKNOWN</span></div>
            <div class=\"kpis\">
                <div class=\"kpi\"><div class=\"kpi-label\">Demanda</div><div id=\"kpiDemand\" class=\"kpi-value\">0 MW</div></div>
                <div class=\"kpi\"><div class=\"kpi-label\">Oferta</div><div id=\"kpiSupply\" class=\"kpi-value\">0 MW</div></div>
                <div class=\"kpi\"><div class=\"kpi-label\">Balance</div><div id=\"kpiBalance\" class=\"kpi-value\">0 MW</div></div>
            </div>
            <div class=\"meta\" id=\"timelineSource\">Fuente timeline: session_history</div>
        </div>

        <div class=\"panel\"><div class=\"title\">Generacion por Tipo</div><canvas id=\"generationChart\"></canvas></div>
        <div class=\"panel\"><div class=\"title\">Demanda vs Oferta</div><canvas id=\"demandSupplyChart\"></canvas></div>
        <div class=\"panel\"><div class=\"title\">Reserva e Intercambios</div><canvas id=\"reserveChart\"></canvas></div>
        <div class=\"panel\"><div class=\"title\">Tendencia Temporal</div><canvas id=\"timelineChart\"></canvas></div>
    </div>

    <script>
        let generationChart;
        let demandSupplyChart;
        let reserveChart;
        let timelineChart;

        function riskColor(level) {
            if (level === 'SAFE') return '#16a34a';
            if (level === 'ALERT') return '#f59e0b';
            if (level === 'CRITICAL') return '#ea580c';
            if (level === 'FAILURE') return '#dc2626';
            return '#64748b';
        }

        function makeCharts() {
            const genCtx = document.getElementById('generationChart');
            generationChart = new Chart(genCtx, {
                type: 'doughnut',
                data: {
                    labels: ['HYDRO', 'THERMAL', 'RENEWABLE'],
                    datasets: [{ data: [0, 0, 0], backgroundColor: ['#0ea5e9', '#f97316', '#22c55e'] }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            });

            const dsCtx = document.getElementById('demandSupplyChart');
            demandSupplyChart = new Chart(dsCtx, {
                type: 'bar',
                data: {
                    labels: ['Demanda', 'Oferta'],
                    datasets: [{ data: [0, 0], backgroundColor: ['#334155', '#2563eb'] }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });

            const reserveCtx = document.getElementById('reserveChart');
            reserveChart = new Chart(reserveCtx, {
                type: 'bar',
                data: {
                    labels: ['Reserva %', 'Import MW', 'Export MW'],
                    datasets: [{ data: [0, 0, 0], backgroundColor: ['#7c3aed', '#0891b2', '#475569'] }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });

            const tlCtx = document.getElementById('timelineChart');
            timelineChart = new Chart(tlCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: 'Demanda', data: [], borderColor: '#1d4ed8', backgroundColor: 'transparent' },
                        { label: 'Oferta', data: [], borderColor: '#16a34a', backgroundColor: 'transparent' },
                        { label: 'Hidro', data: [], borderColor: '#0ea5e9', backgroundColor: 'transparent' },
                        { label: 'Termica', data: [], borderColor: '#f97316', backgroundColor: 'transparent' },
                        { label: 'Renovable', data: [], borderColor: '#22c55e', backgroundColor: 'transparent' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } },
                    elements: { point: { radius: 0 } }
                }
            });
        }

        window.updateDashboard = function(payload) {
            if (!generationChart) makeCharts();

            const gen = payload.generation_by_type || {};
            const demand = Number(payload.demand_mw || 0);
            const supply = Number(payload.supply_mw || 0);
            const balance = Number(payload.balance_mw || 0);
            const reserve = Number(payload.reserve_margin_pct || 0);
            const risk = String(payload.risk_level || 'UNKNOWN');

            document.getElementById('kpiDemand').innerText = demand.toFixed(1) + ' MW';
            document.getElementById('kpiSupply').innerText = supply.toFixed(1) + ' MW';
            document.getElementById('kpiBalance').innerText = balance.toFixed(1) + ' MW';
            document.getElementById('timelineSource').innerText = 'Fuente timeline: ' + String(payload.timeline_source || 'session_history');

            const badge = document.getElementById('riskBadge');
            badge.innerText = risk;
            badge.style.backgroundColor = riskColor(risk);

            generationChart.data.datasets[0].data = [
                Number(gen.HYDRO || 0),
                Number(gen.THERMAL || 0),
                Number(gen.RENEWABLE || 0)
            ];
            generationChart.update('none');

            demandSupplyChart.data.datasets[0].data = [demand, supply];
            demandSupplyChart.update('none');

            reserveChart.data.datasets[0].data = [
                reserve,
                Number(payload.import_mw || 0),
                Number(payload.export_mw || 0)
            ];
            reserveChart.update('none');

            const timeline = payload.timeline || [];
            timelineChart.data.labels = timeline.map(p => String(p.timestamp || ''));
            timelineChart.data.datasets[0].data = timeline.map(p => Number(p.demand_mw || 0));
            timelineChart.data.datasets[1].data = timeline.map(p => Number(p.supply_mw || 0));
            timelineChart.data.datasets[2].data = timeline.map(p => Number(p.hydro_mw || 0));
            timelineChart.data.datasets[3].data = timeline.map(p => Number(p.thermal_mw || 0));
            timelineChart.data.datasets[4].data = timeline.map(p => Number(p.renewable_mw || 0));
            timelineChart.update('none');
        }

        makeCharts();
    </script>
</body>
</html>
        """
