"""Tests for catalog capacity audit helpers."""

import importlib.util
from pathlib import Path


def _load_audit_module():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "audit_central_capacities.py"
    spec = importlib.util.spec_from_file_location("capacity_audit", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_summarize_capacities_has_no_basic_consistency_violations(centrales_json):
    audit = _load_audit_module()
    centrales = audit.load_centrales(centrales_json)
    summary = audit.summarize_capacities(centrales)

    assert isinstance(summary["installed_by_type"], dict)
    assert isinstance(summary["available_by_type"], dict)
    assert summary["issues"] == []


def test_summarize_capacities_flags_available_over_installed():
    audit = _load_audit_module()
    summary = audit.summarize_capacities(
        [
            {
                "id": "bad_1",
                "type": "THERMAL",
                "installed_capacity_mw": 10.0,
                "available_capacity_mw": 20.0,
            }
        ]
    )

    assert len(summary["issues"]) == 1
    assert "available_capacity_mw" in summary["issues"][0]