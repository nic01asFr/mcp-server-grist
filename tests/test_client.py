"""
Tests pour le client Grist.

Ce module teste les fonctionnalités du client Grist pour l'API.
"""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_grist.client import GristClient, get_client, mask_api_key


@pytest.mark.asyncio
async def test_mask_api_key():
    """Teste la fonction de masquage des clés API."""
    # Clé longue
    assert mask_api_key("abcdefghijklmnop") == "abcde...lmnop"
    
    # Clé courte
    assert mask_api_key("abcde") == "[SET]"
    
    # Clé vide
    assert mask_api_key("") == "[SET]"


@pytest.mark.asyncio
async def test_client_initialization(mock_env_vars):
    """Teste l'initialisation du client Grist."""
    client = GristClient(api_key="test_key", api_url="https://test.com/api")
    
    assert client.api_key == "test_key"
    assert client.api_url == "https://test.com/api"
    assert client.headers["Authorization"] == "Bearer test_key"
    assert client.headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_get_client(mock_env_vars):
    """Teste la fonction get_client."""
    client = get_client()
    
    assert client.api_key == "test_api_key"
    assert client.api_url == "https://test-api.getgrist.com/api"


@pytest.mark.asyncio
async def test_get_client_missing_api_key(monkeypatch):
    """Teste get_client sans clé API."""
    # Supprimer toutes les variables d'environnement liées à Grist
    monkeypatch.delenv("GRIST_API_KEY", raising=False)
    monkeypatch.delenv("GRIST_API_URL", raising=False)
    monkeypatch.delenv("GRIST_API_HOST", raising=False)
    
    # Patch la fonction load_dotenv pour qu'elle ne charge pas le fichier .env
    with patch("mcp_server_grist.client.load_dotenv", return_value=None):
        with pytest.raises(ValueError, match="GRIST_API_KEY environment variable is not set"):
            get_client()


@pytest.mark.asyncio
async def test_request_success():
    """Teste la méthode _request avec succès."""
    client = GristClient(api_key="test_key", api_url="https://test.com/api")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_response.raise_for_status = MagicMock()
    
    mock_client = AsyncMock()
    mock_client.request.return_value = mock_response
    
    with patch("httpx.AsyncClient", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_client), __aexit__=AsyncMock())):
        result = await client._request("GET", "/test")
        
    assert result == {"data": "test"}
    mock_client.request.assert_called_once()


@pytest.mark.asyncio
async def test_request_error_handling():
    """Teste que la méthode _request gère correctement les erreurs."""
    client = GristClient(api_key="test_key", api_url="https://test.com/api")
    
    # Mock du client HTTP qui lève une exception
    mock_client = AsyncMock()
    mock_client.request.side_effect = Exception("Test error")
    
    # Patch AsyncClient pour retourner notre mock
    with patch("httpx.AsyncClient", return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_client),
        __aexit__=AsyncMock()
    )):
        # Le client doit gérer l'exception
        try:
            await client._request("GET", "/test")
            assert False, "L'exception n'a pas été levée"
        except ValueError as e:
            # Vérifie que l'erreur est bien convertie en ValueError
            assert "Test error" in str(e)


@pytest.mark.asyncio
async def test_list_orgs():
    """Teste la méthode list_orgs."""
    client = GristClient(api_key="test_key", api_url="https://test.com/api")
    
    # Mock de la réponse
    mock_orgs_data = [
        {"id": "org1", "name": "Org 1"},
        {"id": "org2", "name": "Org 2"}
    ]
    
    # Patch la méthode _request
    with patch.object(client, "_request", AsyncMock(return_value=mock_orgs_data)):
        orgs = await client.list_orgs()
        
    assert len(orgs) == 2
    assert orgs[0].id == "org1"
    assert orgs[0].name == "Org 1"
    assert orgs[1].id == "org2"
    assert orgs[1].name == "Org 2"


@pytest.mark.asyncio
async def test_list_workspaces():
    """Teste la méthode list_workspaces."""
    client = GristClient(api_key="test_key", api_url="https://test.com/api")
    
    # Mock de la réponse
    mock_workspaces_data = [
        {"id": 1, "name": "Workspace 1"},
        {"id": 2, "name": "Workspace 2"}
    ]
    
    # Patch la méthode _request
    with patch.object(client, "_request", AsyncMock(return_value=mock_workspaces_data)):
        workspaces = await client.list_workspaces("org1")
        
    assert len(workspaces) == 2
    assert workspaces[0].id == 1
    assert workspaces[0].name == "Workspace 1"
    assert workspaces[1].id == 2
    assert workspaces[1].name == "Workspace 2"


@pytest.mark.asyncio
async def test_add_records():
    """Teste la méthode add_records."""
    client = GristClient(api_key="test_key", api_url="https://test.com/api")
    
    # Données d'entrée
    records = [
        {"name": "Test 1", "value": 100},
        {"name": "Test 2", "value": 200}
    ]
    
    # Mock de la réponse
    mock_response = {
        "records": [
            {"id": 1, "fields": {"name": "Test 1", "value": 100}},
            {"id": 2, "fields": {"name": "Test 2", "value": 200}}
        ]
    }
    
    # Patch la méthode _request
    with patch.object(client, "_request", AsyncMock(return_value=mock_response)):
        record_ids = await client.add_records("doc1", "table1", records)
        
    assert record_ids == [1, 2]