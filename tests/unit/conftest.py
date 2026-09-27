"""Unit tests must not contact paid providers or production services."""

import os
import tempfile
from pathlib import Path

import httpx
import pytest

# Set before test modules import application state. Lifespan tests must never
# recover or rewrite a developer's saved jobs or announcement queue.
_storage = tempfile.TemporaryDirectory(prefix="council-unit-")
for _key, _directory in {
    "ANALYSIS_OUTPUTS_DIR": "outputs",
    "ANALYSIS_JOBS_DIR": "jobs",
    "PORTFOLIO_POSITIONING_OUTPUTS_DIR": "portfolio",
    "ANALYSIS_PREPASS_DIR": "prepass",
}.items():
    os.environ[_key] = str(Path(_storage.name) / _directory)


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    async_send, sync_send = httpx.AsyncClient.send, httpx.Client.send
    local_hosts = {"test", "testserver", "localhost", "127.0.0.1", "::1"}

    async def guarded_async(client, request, *args, **kwargs):
        if request.url.host not in local_hosts and not isinstance(client._transport, (httpx.MockTransport, httpx.ASGITransport)):
            raise AssertionError(f"External HTTP is disabled in unit tests: {request.url.host}")
        return await async_send(client, request, *args, **kwargs)

    def guarded_sync(client, request, *args, **kwargs):
        if request.url.host not in local_hosts and not isinstance(client._transport, httpx.MockTransport):
            raise AssertionError(f"External HTTP is disabled in unit tests: {request.url.host}")
        return sync_send(client, request, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "send", guarded_async)
    monkeypatch.setattr(httpx.Client, "send", guarded_sync)
