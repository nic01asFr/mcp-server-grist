"""
Tests pour les outils de gestion des accès.

Ce module teste les outils MCP pour la gestion des accès aux ressources Grist.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server_grist.tools.access import (
    list_organization_access,
    modify_organization_access,
    list_workspace_access,
    modify_workspace_access,
    list_document_access,
    modify_document_access
)


@pytest.mark.asyncio
async def test_list_organization_access(mock_grist_client, mock_ctx):
    """Teste l'outil list_organization_access."""
    # Configuration du mock
    mock_access_info = {
        "users": {
            "user1@example.com": "owners",
            "user2@example.com": "editors"
        }
    }
    mock_grist_client.list_org_access.return_value = mock_access_info
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.access.get_client", return_value=mock_grist_client):
        result = await list_organization_access("org1", mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "récupérés avec succès" in result["message"]
    assert result["access"] == mock_access_info
    
    # Vérifier que la méthode a été appelée avec le bon paramètre
    mock_grist_client.list_org_access.assert_called_once_with("org1")


@pytest.mark.asyncio
async def test_modify_organization_access(mock_grist_client, mock_ctx):
    """Teste l'outil modify_organization_access."""
    # Configuration du mock
    mock_grist_client.modify_org_access.return_value = None
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.access.get_client", return_value=mock_grist_client):
        result = await modify_organization_access("org1", "user@example.com", "editors", mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "avec succès" in result["message"]
    
    # Vérifier que la méthode a été appelée avec les bons paramètres
    mock_grist_client.modify_org_access.assert_called_once()
    args, kwargs = mock_grist_client.modify_org_access.call_args
    assert args[0] == "org1"
    assert "users" in args[1]
    assert args[1]["users"]["user@example.com"] == "editors"


@pytest.mark.asyncio
async def test_modify_organization_access_invalid_level(mock_grist_client, mock_ctx):
    """Teste l'outil modify_organization_access avec un niveau d'accès invalide."""
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.access.get_client", return_value=mock_grist_client):
        result = await modify_organization_access("org1", "user@example.com", "invalid", mock_ctx)
    
    # Vérifications
    assert result["success"] is False
    assert "invalide" in result["message"]
    
    # Vérifier que la méthode n'a pas été appelée
    mock_grist_client.modify_org_access.assert_not_called()


@pytest.mark.asyncio
async def test_list_document_access(mock_grist_client, mock_ctx):
    """Teste l'outil list_document_access."""
    # Configuration du mock
    mock_access_info = {
        "users": {
            "user1@example.com": "owners",
            "user2@example.com": "editors"
        }
    }
    mock_grist_client.list_doc_access.return_value = mock_access_info
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.access.get_client", return_value=mock_grist_client):
        result = await list_document_access("doc1", mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "récupérés avec succès" in result["message"]
    assert result["access"] == mock_access_info
    
    # Vérifier que la méthode a été appelée avec le bon paramètre
    mock_grist_client.list_doc_access.assert_called_once_with("doc1")
