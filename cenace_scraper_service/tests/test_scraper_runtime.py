"""Runtime compatibility tests for sync scraper wrapper."""

import asyncio

import pytest

from src.scraper.cenace_scraper import CENACEScraper, CENACEScraperSync


def test_build_event_loop_windows_prefers_proactor(monkeypatch):
    proactor_cls = getattr(asyncio, "ProactorEventLoop", None)
    if proactor_cls is None:
        pytest.skip("ProactorEventLoop not available in this runtime")

    monkeypatch.setattr("src.scraper.cenace_scraper.sys.platform", "win32")

    loop = CENACEScraperSync._build_event_loop()
    try:
        assert isinstance(loop, proactor_cls)
    finally:
        loop.close()


def test_build_event_loop_non_windows_uses_default(monkeypatch):
    expected_loop = asyncio.new_event_loop()

    def fake_new_event_loop():
        return expected_loop

    monkeypatch.setattr("src.scraper.cenace_scraper.sys.platform", "linux")
    monkeypatch.setattr("src.scraper.cenace_scraper.asyncio.new_event_loop", fake_new_event_loop)

    loop = CENACEScraperSync._build_event_loop()
    try:
        assert loop is expected_loop
    finally:
        loop.close()


def test_sync_wrapper_closes_loop_on_success(monkeypatch):
    scraper = CENACEScraperSync()
    custom_loop = asyncio.new_event_loop()

    async def fake_async_scrape(self):
        return {"ok": True}

    monkeypatch.setattr(CENACEScraperSync, "_build_event_loop", staticmethod(lambda: custom_loop))
    monkeypatch.setattr(CENACEScraper, "scrape_production_data", fake_async_scrape)

    result = scraper.scrape_production_data()
    assert result == {"ok": True}
    assert custom_loop.is_closed()


def test_sync_wrapper_closes_loop_on_error(monkeypatch):
    scraper = CENACEScraperSync()
    custom_loop = asyncio.new_event_loop()

    async def fake_async_scrape_raises(self):
        raise RuntimeError("boom")

    monkeypatch.setattr(CENACEScraperSync, "_build_event_loop", staticmethod(lambda: custom_loop))
    monkeypatch.setattr(CENACEScraper, "scrape_production_data", fake_async_scrape_raises)

    with pytest.raises(RuntimeError, match="boom"):
        scraper.scrape_production_data()

    assert custom_loop.is_closed()
