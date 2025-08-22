"""
Tests de conformité MCP.

Ce module vérifie que les outils MCP sont conformes aux standards MCP.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server_grist.tools.navigation import list_organizations, list_records
from mcp_server_grist.tools.records import add_grist_records, update_grist_records, delete_grist_records
from mcp_server_grist.tools.queries import filter_sql_query, execute_sql_query


@pytest.mark.asyncio
async def test_navigation_tool_response_format(mock_grist_client, mock_ctx):
    """Vérifie que les outils de navigation retournent le format de réponse MCP correct."""
    # Configuration du mock
    mock_grist_client.list_orgs.return_value = []
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.navigation.get_client", return_value=mock_grist_client):
        result = await list_organizations(mock_ctx)
    
    # Vérifications du format de réponse MCP
    assert isinstance(result, dict), "La réponse doit être un dictionnaire"
    assert "success" in result, "La réponse doit contenir un champ 'success'"
    assert isinstance(result["success"], bool), "Le champ 'success' doit être un booléen"
    assert "message" in result, "La réponse doit contenir un champ 'message'"
    assert isinstance(result["message"], str), "Le champ 'message' doit être une chaîne"


@pytest.mark.asyncio
async def test_records_tool_response_format(mock_grist_client, mock_ctx):
    """Vérifie que les outils de gestion des enregistrements retournent le format de réponse MCP correct."""
    # Configuration du mock
    mock_grist_client.add_records.return_value = [1]
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await add_grist_records("doc1", "table1", [{"name": "Test"}], mock_ctx)
    
    # Vérifications du format de réponse MCP
    assert isinstance(result, dict), "La réponse doit être un dictionnaire"
    assert "success" in result, "La réponse doit contenir un champ 'success'"
    assert isinstance(result["success"], bool), "Le champ 'success' doit être un booléen"
    assert "message" in result, "La réponse doit contenir un champ 'message'"
    assert isinstance(result["message"], str), "Le champ 'message' doit être une chaîne"
    assert "record_ids" in result, "La réponse doit contenir un champ 'record_ids'"


@pytest.mark.asyncio
async def test_error_response_format(mock_grist_client, mock_ctx):
    """Vérifie que les erreurs sont formatées correctement selon MCP."""
    # Configuration du mock pour lever une exception
    mock_grist_client.list_orgs.side_effect = ValueError("API Error")
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.navigation.get_client", return_value=mock_grist_client):
        result = await list_organizations(mock_ctx)
    
    # Vérifications du format d'erreur MCP
    assert isinstance(result, dict), "La réponse d'erreur doit être un dictionnaire"
    assert "success" in result, "La réponse d'erreur doit contenir un champ 'success'"
    assert result["success"] is False, "Le champ 'success' doit être False en cas d'erreur"
    assert "message" in result, "La réponse d'erreur doit contenir un champ 'message'"
    assert isinstance(result["message"], str), "Le champ 'message' doit être une chaîne"
    assert "Error" in result["message"], "Le message doit contenir des informations sur l'erreur"


@pytest.mark.asyncio
async def test_add_records_response_format(mock_grist_client, mock_ctx):
    """Vérifie spécifiquement que add_grist_records retourne un dictionnaire et non une liste."""
    # Configuration du mock
    mock_grist_client.add_records.return_value = [1, 2, 3]
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await add_grist_records("doc1", "table1", [{"name": "Test"}], mock_ctx)
    
    # Vérifications spécifiques pour add_grist_records
    assert isinstance(result, dict), "add_grist_records doit retourner un dictionnaire"
    assert "success" in result, "La réponse doit contenir un champ 'success'"
    assert "message" in result, "La réponse doit contenir un champ 'message'"
    assert "record_ids" in result, "La réponse doit contenir un champ 'record_ids'"
    assert isinstance(result["record_ids"], list), "record_ids doit être une liste"