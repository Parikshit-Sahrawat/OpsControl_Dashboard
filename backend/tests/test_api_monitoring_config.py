"""DEV-04.3 contract tests: safe API configuration and worker compatibility."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.api_monitoring_config import build_api_config


@pytest.fixture
def worker():
    return SimpleNamespace(allowed_hosts=["api.example.test"], allowed_cidrs=["203.0.113.0/24"])


@pytest.fixture
def source():
    return SimpleNamespace(endpoint="https://api.example.test/health")


def test_get_defaults_preserve_existing_remote_worker_protocol(source, worker):
    config = build_api_config({}, source, worker)
    assert config == {
        "url": "https://api.example.test/health",
        "expected_status": 200,
        "timeout_seconds": 8,
        "method": "GET",
    }


@pytest.mark.parametrize("config", [
    {"method": "POST"},
    {"method": "DELETE"},
    {"method": "HEAD"},
    {"method": "get"},
    {"headers": {"Authorization": "Bearer secret"}},
    {"headers": {"Accept": "application/json"}},
    {"body": {"password": "secret"}},
    {"query": {"token": "sensitive"}},
    {"url": "http://api.example.test/health"},
    {"url": "https://evil.example.test/health"},
    {"url": "https://api.example.test/health?secret=x"},
    {"expected_status": True},
    {"expected_status": 600},
    {"timeout_seconds": 0},
    {"timeout_seconds": 11},
])
def test_unsupported_or_unsafe_api_configuration_fails_closed(source, worker, config):
    with pytest.raises(HTTPException) as error:
        build_api_config(config, source, worker)
    assert error.value.status_code == 422


def test_valid_explicit_get_preserves_status_and_timeout(source, worker):
    config = build_api_config({"method": "GET", "expected_status": 204, "timeout_seconds": 5}, source, worker)
    assert config["method"] == "GET"
    assert config["expected_status"] == 204
    assert config["timeout_seconds"] == 5
