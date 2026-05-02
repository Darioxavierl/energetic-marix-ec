"""Integration smoke tests against live local microservice."""

import pytest

from config.settings import MICROSERVICE_BASE_URL, MICROSERVICE_TIMEOUT_SECONDS
from src.infrastructure.api.cenace_client import CENACEClient, CENACEClientError


@pytest.mark.integration
def test_live_microservice_health_smoke():
    client = CENACEClient(MICROSERVICE_BASE_URL, timeout_seconds=MICROSERVICE_TIMEOUT_SECONDS)
    try:
        payload = client.get_health()
    except CENACEClientError as exc:
        pytest.skip(f"Microservicio no disponible para integration smoke: {exc}")

    assert "status" in payload
    assert "success_rate" in payload


@pytest.mark.integration
def test_live_microservice_hourly_shape_smoke():
    client = CENACEClient(MICROSERVICE_BASE_URL, timeout_seconds=MICROSERVICE_TIMEOUT_SECONDS)
    try:
        rows = client.get_hourly_demand()
    except CENACEClientError as exc:
        pytest.skip(f"Microservicio no disponible para integration smoke: {exc}")

    assert isinstance(rows, list)
    if rows:
        sample = rows[-1]
        assert "demand_mw" in sample
        assert "hydro_mw" in sample
        assert "thermal_mw" in sample
