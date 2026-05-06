"""End-to-end verification for CENACE data freshness and consistency.

Checks the chain: API -> DB -> optional direct scrape.
Use this to detect where stale or mismatched data appears.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MICROSERVICE_ROOT = PROJECT_ROOT / "cenace_scraper_service"

if str(MICROSERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(MICROSERVICE_ROOT))


@dataclass
class Sample:
    captured_at: datetime
    api_timestamp: datetime | None
    payload: dict[str, Any] | None
    demand_payload: dict[str, Any] | None
    error: str | None


def parse_iso_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def fetch_json(url: str, timeout_seconds: float) -> dict[str, Any]:
    with urlopen(url, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def get_db_snapshot(db_path: Path) -> dict[str, Any]:
    output: dict[str, Any] = {
        "db_access_ok": False,
        "error": None,
        "latest_production": None,
        "latest_scrape_log": None,
        "counts": {},
    }

    if not db_path.exists():
        output["error"] = f"DB not found: {db_path}"
        return output

    try:
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()

        latest_prod = cur.execute(
            """
            SELECT timestamp,total_mwh,hydro_mwh,thermal_mwh,renewable_mwh,import_mwh,export_mwh
            FROM production_snapshots
            ORDER BY timestamp DESC
            LIMIT 1
            """
        ).fetchone()

        latest_log = cur.execute(
            """
            SELECT timestamp,success,error_message,records_inserted,duration_seconds
            FROM scrape_logs
            ORDER BY timestamp DESC
            LIMIT 1
            """
        ).fetchone()

        counts = {
            "production_snapshots": cur.execute("SELECT COUNT(*) FROM production_snapshots").fetchone()[0],
            "plant_generations": cur.execute("SELECT COUNT(*) FROM plant_generations").fetchone()[0],
            "hourly_curves": cur.execute("SELECT COUNT(*) FROM hourly_curves").fetchone()[0],
            "scrape_logs": cur.execute("SELECT COUNT(*) FROM scrape_logs").fetchone()[0],
        }

        output["latest_production"] = latest_prod
        output["latest_scrape_log"] = latest_log
        output["counts"] = counts
        output["db_access_ok"] = True
        con.close()
        return output

    except Exception as exc:  # pragma: no cover - diagnostic script
        output["error"] = str(exc)
        return output


def get_api_sample(base_url: str, timeout_seconds: float) -> Sample:
    captured_at = datetime.now()
    endpoint = f"{base_url.rstrip('/')}/api/v1/production/latest"
    try:
        payload = fetch_json(endpoint, timeout_seconds)
        demand_payload = fetch_json(f"{base_url.rstrip('/')}/api/v1/demand/latest", timeout_seconds)
        api_ts = parse_iso_datetime(payload.get("timestamp"))
        return Sample(
            captured_at=captured_at,
            api_timestamp=api_ts,
            payload=payload,
            demand_payload=demand_payload,
            error=None,
        )
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return Sample(captured_at=captured_at, api_timestamp=None, payload=None, demand_payload=None, error=str(exc))


def run_direct_scrape(timeout_seconds: float) -> dict[str, Any] | None:
    """Run one direct scrape to compare parser output against API/DB.

    This bypasses scheduler/API persistence and helps isolate scraper issues.
    """

    try:
        from src.scraper.cenace_scraper import CENACEScraperSync

        scraper = CENACEScraperSync()
        data = scraper.scrape_production_data()
        if not data:
            return None
        return {
            "timestamp": str(data.get("timestamp", "")),
            "total_mwh": float(data.get("total_mwh", 0.0) or 0.0),
            "hydro_mwh": float(data.get("hydro_mwh", 0.0) or 0.0),
            "thermal_mwh": float(data.get("thermal_mwh", 0.0) or 0.0),
            "renewable_mwh": float(data.get("renewable_mwh", 0.0) or 0.0),
            "import_mwh": float(data.get("import_mwh", 0.0) or 0.0),
            "export_mwh": float(data.get("export_mwh", 0.0) or 0.0),
            "timeout_seconds": timeout_seconds,
        }
    except Exception as exc:  # pragma: no cover - diagnostic script
        return {"error": str(exc)}


def pct_delta(a: float, b: float) -> float:
    if a == 0 and b == 0:
        return 0.0
    denom = abs(a) if abs(a) > 1e-9 else 1.0
    return ((b - a) / denom) * 100.0


def diagnose(samples: list[Sample], db_snapshot: dict[str, Any], stale_threshold_min: float) -> list[str]:
    findings: list[str] = []

    failed = [s for s in samples if s.error]
    if failed:
        findings.append("API_UNREACHABLE: No se pudo consultar /api/v1/production/latest.")

    latest_api_ts = None
    for sample in reversed(samples):
        if sample.api_timestamp:
            latest_api_ts = sample.api_timestamp
            break

    latest_db_ts = None
    prod = db_snapshot.get("latest_production")
    if prod and prod[0]:
        latest_db_ts = parse_iso_datetime(str(prod[0]))

    now = datetime.now()
    if latest_api_ts is not None:
        age_min = (now - latest_api_ts).total_seconds() / 60.0
        if age_min > stale_threshold_min:
            findings.append(
                f"API_STALE: timestamp API tiene {age_min:.1f} min de antiguedad (umbral {stale_threshold_min:.1f})."
            )

    if latest_db_ts is not None:
        age_db_min = (now - latest_db_ts).total_seconds() / 60.0
        if age_db_min > stale_threshold_min:
            findings.append(
                f"DB_STALE: ultimo production_snapshot tiene {age_db_min:.1f} min de antiguedad (umbral {stale_threshold_min:.1f})."
            )

    if latest_api_ts and latest_db_ts:
        drift_sec = abs((latest_api_ts - latest_db_ts).total_seconds())
        if drift_sec > 120:
            findings.append(
                f"API_DB_DRIFT: API y DB difieren {drift_sec:.0f}s en timestamp del ultimo dato."
            )

    if not findings:
        findings.append("OK: No se detecto staleness evidente en API/DB con esta corrida.")

    return findings


def print_sample_table(samples: list[Sample]) -> None:
    print("\nMuestras API (/production/latest):")
    for i, sample in enumerate(samples, start=1):
        if sample.error:
            print(f"- M{i}: ERROR at {sample.captured_at.isoformat(sep=' ', timespec='seconds')} -> {sample.error}")
            continue
        payload = sample.payload or {}
        demand_payload = sample.demand_payload or {}
        print(
            "- M{i}: cap={cap} api_ts={ts} total={total:.2f} hydro={hydro:.2f} thermal={thermal:.2f} "
            "renew={renew:.2f} import={imp:.2f} export={exp:.2f} demand_latest={demand:.2f}".format(
                i=i,
                cap=sample.captured_at.isoformat(sep=" ", timespec="seconds"),
                ts=(sample.api_timestamp.isoformat(sep=" ", timespec="seconds") if sample.api_timestamp else "N/A"),
                total=float(payload.get("total_mwh", 0.0) or 0.0),
                hydro=float(payload.get("hydro_mwh", 0.0) or 0.0),
                thermal=float(payload.get("thermal_mwh", 0.0) or 0.0),
                renew=float(payload.get("renewable_mwh", 0.0) or 0.0),
                imp=float(payload.get("import_mwh", 0.0) or 0.0),
                exp=float(payload.get("export_mwh", 0.0) or 0.0),
                demand=float(demand_payload.get("demand_total_mw", 0.0) or 0.0),
            )
        )


def print_db_summary(db_snapshot: dict[str, Any]) -> None:
    print("\nEstado DB (cenace.db):")
    if not db_snapshot.get("db_access_ok"):
        print(f"- ERROR: {db_snapshot.get('error')}")
        return

    latest_prod = db_snapshot.get("latest_production")
    latest_log = db_snapshot.get("latest_scrape_log")
    counts = db_snapshot.get("counts", {})

    print(f"- latest production row: {latest_prod}")
    print(f"- latest scrape log row: {latest_log}")
    print(f"- table counts: {counts}")


def compare_direct_vs_api(direct: dict[str, Any] | None, sample: Sample | None) -> None:
    print("\nComparacion scrape directo vs API latest:")
    if not direct:
        print("- No se ejecuto scrape directo.")
        return
    if direct.get("error"):
        print(f"- ERROR scrape directo: {direct.get('error')}")
        return
    if not sample or not sample.payload:
        print("- API latest no disponible para comparar.")
        return

    api = sample.payload
    keys = ["total_mwh", "hydro_mwh", "thermal_mwh", "renewable_mwh", "import_mwh", "export_mwh"]
    print(f"- direct timestamp: {direct.get('timestamp')}")
    print(f"- api timestamp: {sample.api_timestamp.isoformat(sep=' ', timespec='seconds') if sample.api_timestamp else 'N/A'}")
    for key in keys:
        d = float(direct.get(key, 0.0) or 0.0)
        a = float(api.get(key, 0.0) or 0.0)
        delta = pct_delta(d, a)
        print(f"  {key}: direct={d:.2f} api={a:.2f} delta_pct={delta:.2f}%")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify CENACE microservice freshness and consistency.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001", help="Microservice base URL")
    parser.add_argument(
        "--db-path",
        default=str(MICROSERVICE_ROOT / "cenace.db"),
        help="Path to SQLite DB used by microservice",
    )
    parser.add_argument("--samples", type=int, default=3, help="Number of API samples")
    parser.add_argument("--sample-interval-sec", type=float, default=10.0, help="Seconds between API samples")
    parser.add_argument("--timeout-seconds", type=float, default=10.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--stale-threshold-min",
        type=float,
        default=30.0,
        help="Staleness threshold in minutes (recommended: 2 * scheduler interval)",
    )
    parser.add_argument(
        "--direct-scrape",
        action="store_true",
        help="Run one direct scrape and compare against API latest",
    )
    args = parser.parse_args()

    print("=" * 76)
    print("VERIFICACION END-TO-END CENACE (API -> DB -> DIRECT SCRAPE)")
    print("=" * 76)
    print(f"base_url={args.base_url}")
    print(f"db_path={args.db_path}")
    print(f"samples={args.samples} interval_sec={args.sample_interval_sec}")

    samples: list[Sample] = []
    for i in range(args.samples):
        sample = get_api_sample(args.base_url, args.timeout_seconds)
        samples.append(sample)
        if i < args.samples - 1:
            time.sleep(max(0.0, args.sample_interval_sec))

    db_snapshot = get_db_snapshot(Path(args.db_path))
    findings = diagnose(samples, db_snapshot, stale_threshold_min=args.stale_threshold_min)

    print_sample_table(samples)
    print_db_summary(db_snapshot)

    direct_result: dict[str, Any] | None = None
    if args.direct_scrape:
        direct_result = run_direct_scrape(timeout_seconds=args.timeout_seconds)
        latest_ok_sample = next((s for s in reversed(samples) if s.payload is not None), None)
        compare_direct_vs_api(direct_result, latest_ok_sample)

    print("\nHallazgos:")
    for finding in findings:
        print(f"- {finding}")

    exit_code = 0
    if any(f.startswith("API_UNREACHABLE") or f.startswith("API_STALE") or f.startswith("DB_STALE") for f in findings):
        exit_code = 2

    print("=" * 76)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
