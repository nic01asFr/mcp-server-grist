"""
Configuration pour les tests pytest.

Ce fichier contient les fixtures et configurations communes pour tous les tests.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch

from mcp_server_grist.client import GristClient


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Configure les variables d'environnement pour les tests."""
    monkeypatch.setenv("GRIST_API_KEY", "test_api_key")
    monkeypatch.setenv("GRIST_API_HOST", "https://test-api.getgrist.com/api")


@pytest.fixture
def mock_grist_client():
    """Crée un mock du client Grist pour les tests."""
    client = AsyncMock(spec=GristClient)
    client.api_key = "test_api_key"
    client.api_url = "https://test-api.getgrist.com/api"
    client.headers = {
        "Authorization": f"Bearer test_api_key",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    return client


@pytest.fixture
def mock_ctx():
    """Crée un mock du contexte MCP pour les tests."""
    ctx = AsyncMock()
    return ctx
