"""Audit local central catalog capacities and optional live snapshot compatibility."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.application.plant_generation_mapper import map_live_generation_to_centrales_with_diagnostics
from src.infrastructure.api.cenace_client import CENACEClient, CENACEClientError


def load_centrales(centrales_path: Path) -> list[dict]:
    payload = json.loads(centrales_path.read_text(encoding="utf-8"))
    centrales = payload.get("data", {}).get("centrales", [])
    if not isinstance(centrales, list):
        return []
    return centrales


def summarize_capacities(centrales: list[dict]) -> dict:
    totals_installed = defaultdict(float)
    totals_available = defaultdict(float)
    issues: list[str] = []

    for central in centrales:
        cid = str(central.get("id", ""))
        ctype = str(central.get("type", "OTHER")).upper()
        installed = float(central.get("installed_capacity_mw", 0.0) or 0.0)
        available = float(central.get("available_capacity_mw", 0.0) or 0.0)

        totals_installed[ctype] += max(0.0, installed)
        totals_available[ctype] += max(0.0, available)

        if installed <= 0.0:
            issues.append(f"{cid}: installed_capacity_mw <= 0 ({installed:.2f})")
        if available < 0.0:
            issues.append(f"{cid}: available_capacity_mw < 0 ({available:.2f})")
        if available > installed and installed > 0.0:
            issues.append(
                f"{cid}: available_capacity_mw ({available:.2f}) > installed_capacity_mw ({installed:.2f})"
            )

    return {
        "installed_by_type": dict(totals_installed),
        "available_by_type": dict(totals_available),
        "issues": issues,
    }


def compare_with_live(centrales: list[dict], base_url: str, timeout_seconds: float) -> dict:
    client = CENACEClient(base_url=base_url, timeout_seconds=timeout_seconds)
    production = client.get_latest_production()
    plants = client.get_latest_plants()

    mapped_by_id, diagnostics = map_live_generation_to_centrales_with_diagnostics(
        centrales=centrales,
        live_plants=plants,
    )

    mapped_by_type = defaultdict(float)
    for central in centrales:
        cid = str(central.get("id", ""))
        ctype = str(central.get("type", "OTHER")).upper()
        mapped_by_type[ctype] += max(0.0, float(mapped_by_id.get(cid, 0.0) or 0.0))

    live_reference = {
        "HYDRO": float(production.get("hydro_mwh", 0.0) or 0.0),
        "THERMAL": float(production.get("thermal_mwh", 0.0) or 0.0),
        "RENEWABLE": float(production.get("renewable_mwh", 0.0) or 0.0),
    }

    return {
        "timestamp": str(production.get("timestamp", "")),
        "live_reference_by_type": live_reference,
        "mapped_live_to_catalog_by_type": dict(mapped_by_type),
        "mapping_diagnostics": diagnostics,
    }


def print_report(capacity_summary: dict, live_summary: dict | None) -> None:
    print("=" * 72)
    print("CATALOGO DE CENTRALES - AUDITORIA DE CAPACIDADES")
    print("=" * 72)

    print("\nCapacidad instalada por tipo (MW):")
    for ctype, value in sorted(capacity_summary["installed_by_type"].items()):
        print(f"- {ctype:8} {value:10.2f}")

    print("\nCapacidad disponible inicial por tipo (MW):")
    for ctype, value in sorted(capacity_summary["available_by_type"].items()):
        print(f"- {ctype:8} {value:10.2f}")

    issues = capacity_summary.get("issues", [])
    print(f"\nReglas de consistencia: {len(issues)} issue(s)")
    for issue in issues:
        print(f"- {issue}")

    if not live_summary:
        return

    print("\nComparacion contra ultimo snapshot live")
    print(f"- Timestamp: {live_summary.get('timestamp', '')}")

    live_reference = live_summary.get("live_reference_by_type", {})
    mapped = live_summary.get("mapped_live_to_catalog_by_type", {})

    hydro_gap = float(live_reference.get("HYDRO", 0.0)) - float(mapped.get("HYDRO", 0.0))
    thermal_gap = float(live_reference.get("THERMAL", 0.0)) - float(mapped.get("THERMAL", 0.0))

    print("- Live referencia (MWh):")
    print(f"  HYDRO={float(live_reference.get('HYDRO', 0.0)):.2f} THERMAL={float(live_reference.get('THERMAL', 0.0)):.2f} "
          f"RENEWABLE={float(live_reference.get('RENEWABLE', 0.0)):.2f}")
    print("- Live mapeado al catalogo (MW por central):")
    print(f"  HYDRO={float(mapped.get('HYDRO', 0.0)):.2f} THERMAL={float(mapped.get('THERMAL', 0.0)):.2f} "
          f"WIND={float(mapped.get('WIND', 0.0)):.2f} SOLAR={float(mapped.get('SOLAR', 0.0)):.2f}")
    print(f"- Gap estimado HYDRO={hydro_gap:.2f} THERMAL={thermal_gap:.2f}")

    diag = live_summary.get("mapping_diagnostics", {})
    print(f"- Mapping direct_matches={int(diag.get('direct_matches', 0))} distributed_matches={int(diag.get('distributed_matches', 0))}")
    unmatched = diag.get("unmatched_pool_by_type", {})
    if unmatched:
        print(f"- Unmatched pool por tipo: {unmatched}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit central capacities from local catalog and optional live data.")
    parser.add_argument(
        "--centrales-json",
        default=str(PROJECT_ROOT / "data" / "centrales" / "centrales_ecuador.json"),
        help="Path to centrales_ecuador.json",
    )
    parser.add_argument(
        "--microservice-url",
        default="",
        help="Optional CENACE scraper base URL (example: http://127.0.0.1:8001)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="HTTP timeout when requesting live data",
    )
    args = parser.parse_args()

    centrales_path = Path(args.centrales_json)
    if not centrales_path.exists():
        print(f"Archivo no encontrado: {centrales_path}")
        return 2

    centrales = load_centrales(centrales_path)
    summary = summarize_capacities(centrales)

    live_summary = None
    if args.microservice_url.strip():
        try:
            live_summary = compare_with_live(
                centrales=centrales,
                base_url=args.microservice_url.strip(),
                timeout_seconds=args.timeout_seconds,
            )
        except CENACEClientError as exc:
            print(f"No se pudo consultar microservicio: {exc}")

    print_report(summary, live_summary)
    return 1 if summary.get("issues") else 0


if __name__ == "__main__":
    raise SystemExit(main())
