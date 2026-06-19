from __future__ import annotations

import time

import pytest

from app.client import EndpointSpec, ModeTourApiClient, ModeTourApiError
from app.config import Settings


def build_client() -> ModeTourApiClient:
    return ModeTourApiClient(
        Settings(
            header_cache_json=(
                '{"accept":"application/json","referer":"https://www.modetour.com/",'
                '"user-agent":"Mozilla/5.0","x-platform":"WEB","x-salespartner":"false",'
                '"x-username":"","x-userid":"","x-userdepartment":"","modewebapireqheader":"encoded-header"}'
            )
        )
    )


def test_fetch_all_runs_endpoints_in_parallel(monkeypatch: pytest.MonkeyPatch) -> None:
    client = build_client()
    client._endpoints = (
        EndpointSpec("one", "/one"),
        EndpointSpec("two", "/two"),
        EndpointSpec("three", "/three"),
    )

    def fake_fetch_one(spec: EndpointSpec, product_no: str) -> str:
        time.sleep(0.2)
        return f"{spec.name}:{product_no}"

    monkeypatch.setattr(client, "_fetch_one", fake_fetch_one)

    started_at = time.perf_counter()
    result = client.fetch_all("104642639")
    elapsed = time.perf_counter() - started_at

    assert result == {
        "one": "one:104642639",
        "two": "two:104642639",
        "three": "three:104642639",
    }
    assert elapsed < 0.45


def test_fetch_all_propagates_endpoint_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    client = build_client()
    client._endpoints = (
        EndpointSpec("ok", "/ok"),
        EndpointSpec("bad", "/bad"),
    )

    def fake_fetch_one(spec: EndpointSpec, product_no: str) -> str:
        if spec.name == "bad":
            raise ModeTourApiError("boom")
        return "ok"

    monkeypatch.setattr(client, "_fetch_one", fake_fetch_one)

    with pytest.raises(ModeTourApiError):
        client.fetch_all("104642639")
