"""HTTP client to consume the local CENACE scraper microservice."""

import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


class CENACEClientError(Exception):
    """Raised when the scraper microservice cannot be consumed safely."""


class CENACEClient:
    """Simple typed client for local microservice endpoints."""

    def __init__(self, base_url: str, timeout_seconds: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_health(self) -> dict:
        """Return health payload from microservice."""

        return self._get_json("/api/v1/health")

    def get_latest_production(self) -> dict:
        """Return the latest production snapshot payload."""

        return self._get_json("/api/v1/production/latest")

    def get_latest_demand(self) -> dict:
        """Return latest consolidated demand payload from demand real-time tab."""

        return self._get_json("/api/v1/demand/latest")

    def get_latest_plants(self) -> list[dict]:
        """Return latest plant generation list."""

        return self._get_json("/api/v1/plants/latest")

    def get_hourly_demand(self, date_iso: str | None = None) -> list[dict]:
        """Return hourly demand curve for a date or latest 24h."""

        query = ""
        if date_iso:
            query = "?" + urlencode({"date": date_iso})
        return self._get_json(f"/api/v1/demand/hourly{query}")

    def _get_json(self, path: str):
        """Execute GET and parse JSON payload."""

        url = f"{self.base_url}{path}"
        try:
            with urlopen(url, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise CENACEClientError(f"Error consumiendo {url}: {exc}") from exc

    @staticmethod
    def parse_iso_datetime(value: str | None) -> datetime | None:
        """Parse ISO timestamp from API payload."""

        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
