"""
Tests pour les outils de navigation MCP.

Ce module teste les outils MCP pour la navigation dans la structure Grist.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server_grist.models import GristOrg, GristWorkspace, GristDocument, GristTable, GristColumn
from mcp_server_grist.tools.navigation import (
    list_organizations,
    list_workspaces,
    list_documents,
    list_tables,
    list_columns,
    list_records
)


@pytest.mark.asyncio
async def test_list_organizations(mock_grist_client, mock_ctx):
    """Teste l'outil list_organizations."""
    # Configuration du mock
    mock_orgs = [
        GristOrg(id="org1", name="Org 1"),
        GristOrg(id="org2", name="Org 2")
    ]
    mock_grist_client.list_orgs.return_value = mock_orgs
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.navigation.get_client", return_value=mock_grist_client):
        result = await list_organizations(mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "Found 2 organizations" in result["message"]
    assert len(result["organizations"]) == 2
    assert result["organizations"][0]["id"] == "org1"
    assert result["organizations"][1]["name"] == "Org 2"


@pytest.mark.asyncio
async def test_list_workspaces(mock_grist_client, mock_ctx):
    """Teste l'outil list_workspaces."""
    # Configuration du mock
    mock_workspaces = [
        GristWorkspace(id=1, name="Workspace 1"),
        GristWorkspace(id=2, name="Workspace 2")
    ]
    mock_grist_client.list_workspaces.return_value = mock_workspaces
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.navigation.get_client", return_value=mock_grist_client):
        result = await list_workspaces("org1", mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "Found 2 workspaces" in result["message"]
    assert len(result["workspaces"]) == 2
    assert result["workspaces"][0]["id"] == 1
    assert result["workspaces"][1]["name"] == "Workspace 2"
    
    # Vérifier que la méthode a été appelée avec le bon paramètre
    mock_grist_client.list_workspaces.assert_called_once_with("org1")


@pytest.mark.asyncio
async def test_list_documents(mock_grist_client, mock_ctx):
    """Teste l'outil list_documents."""
    # Configuration du mock
    mock_documents = [
        GristDocument(id="doc1", name="Document 1"),
        GristDocument(id="doc2", name="Document 2")
    ]
    mock_grist_client.list_documents.return_value = mock_documents
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.navigation.get_client", return_value=mock_grist_client):
        result = await list_documents(1, mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "Found 2 documents" in result["message"]
    assert len(result["documents"]) == 2
    assert result["documents"][0]["id"] == "doc1"
    assert result["documents"][1]["name"] == "Document 2"
    
    # Vérifier que la méthode a été appelée avec le bon paramètre
    mock_grist_client.list_documents.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_list_tables(mock_grist_client, mock_ctx):
    """Teste l'outil list_tables."""
    # Configuration du mock
    mock_tables = [
        GristTable(id="table1", fields={"tableId": "table1"}),
        GristTable(id="table2", fields={"tableId": "table2"})
    ]
    mock_grist_client.list_tables.return_value = mock_tables
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.navigation.get_client", return_value=mock_grist_client):
        result = await list_tables("doc1", mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "Found 2 tables" in result["message"]
    assert len(result["tables"]) == 2
    assert result["tables"][0]["id"] == "table1"
    assert result["tables"][1]["id"] == "table2"
    
    # Vérifier que la méthode a été appelée avec le bon paramètre
    mock_grist_client.list_tables.assert_called_once_with("doc1")


@pytest.mark.asyncio
async def test_list_columns(mock_grist_client, mock_ctx):
    """Teste l'outil list_columns."""
    # Configuration du mock
    mock_columns = [
        GristColumn(id="col1", fields={"label": "Column 1", "type": "Text"}),
        GristColumn(id="col2", fields={"label": "Column 2", "type": "Numeric"})
    ]
    mock_grist_client.list_columns.return_value = mock_columns
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.navigation.get_client", return_value=mock_grist_client):
        result = await list_columns("doc1", "table1", mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "Found 2 columns" in result["message"]
    assert len(result["columns"]) == 2
    assert result["columns"][0]["id"] == "col1"
    assert result["columns"][1]["fields"]["label"] == "Column 2"
    
    # Vérifier que la méthode a été appelée avec les bons paramètres
    mock_grist_client.list_columns.assert_called_once_with("doc1", "table1")


@pytest.mark.asyncio
async def test_list_records(mock_grist_client, mock_ctx):
    """Teste l'outil list_records."""
    # Configuration du mock
    from mcp_server_grist.models import GristRecord
    
    mock_records = [
        GristRecord(id=1, fields={"name": "Record 1", "value": 100}),
        GristRecord(id=2, fields={"name": "Record 2", "value": 200})
    ]
    mock_grist_client.list_records.return_value = mock_records
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.navigation.get_client", return_value=mock_grist_client):
        result = await list_records("doc1", "table1", sort="name", limit=10, ctx=mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "Found 2 records" in result["message"]
    assert len(result["records"]) == 2
    assert result["records"][0]["id"] == 1
    assert result["records"][1]["fields"]["name"] == "Record 2"
    assert result["record_count"] == 2
    
    # Vérifier que la méthode a été appelée avec les bons paramètres
    mock_grist_client.list_records.assert_called_once_with("doc1", "table1", sort="name", limit=10)
