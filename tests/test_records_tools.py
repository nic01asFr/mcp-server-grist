"""
Tests pour les outils de gestion des enregistrements MCP.

Ce module teste les outils MCP pour la manipulation des enregistrements Grist.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server_grist.tools.records import (
    add_grist_records,
    add_grist_records_safe,
    update_grist_records,
    delete_grist_records
)


@pytest.mark.asyncio
async def test_add_grist_records(mock_grist_client, mock_ctx):
    """Teste l'outil add_grist_records."""
    # Données d'entrée
    doc_id = "doc1"
    table_id = "table1"
    records = [
        {"name": "Test 1", "value": 100},
        {"name": "Test 2", "value": 200}
    ]
    
    # Configuration du mock
    mock_grist_client.add_records.return_value = [1, 2]
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await add_grist_records(doc_id, table_id, records, mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "2 enregistrements ajoutés" in result["message"]
    assert result["record_ids"] == [1, 2]
    
    # Vérifier que la méthode a été appelée avec les bons paramètres
    mock_grist_client.add_records.assert_called_once_with(doc_id, table_id, records)


@pytest.mark.asyncio
async def test_add_grist_records_error(mock_grist_client, mock_ctx):
    """Teste l'outil add_grist_records avec une erreur."""
    # Données d'entrée
    doc_id = "doc1"
    table_id = "table1"
    records = [
        {"name": "Test 1", "value": 100},
        {"name": "Test 2", "value": 200}
    ]
    
    # Configuration du mock pour lever une exception
    mock_grist_client.add_records.side_effect = ValueError("API Error")
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await add_grist_records(doc_id, table_id, records, mock_ctx)
    
    # Vérifications
    assert result["success"] is False
    assert "Erreur lors de l'ajout des enregistrements" in result["message"]
    assert result["record_ids"] == []


@pytest.mark.asyncio
async def test_add_grist_records_safe_success(mock_grist_client, mock_ctx):
    """Teste l'outil add_grist_records_safe avec succès."""
    # Données d'entrée
    doc_id = "doc1"
    table_id = "table1"
    records = [
        {"name": "Test 1", "value": 100},
        {"name": "Test 2", "value": 200}
    ]
    
    # Configuration des mocks
    mock_grist_client.validate_table_exists.return_value = {"exists": True}
    mock_grist_client.validate_columns_exist.return_value = {"valid": True}
    mock_grist_client.add_records.return_value = [1, 2]
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await add_grist_records_safe(doc_id, table_id, records, mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "2 enregistrements ajoutés avec succès après validation" in result["message"]
    assert result["record_ids"] == [1, 2]


@pytest.mark.asyncio
async def test_add_grist_records_safe_invalid_table(mock_grist_client, mock_ctx):
    """Teste add_grist_records_safe avec une table invalide."""
    # Données d'entrée
    doc_id = "doc1"
    table_id = "invalid_table"
    records = [{"name": "Test"}]
    
    # Configuration du mock pour une table inexistante
    mock_grist_client.validate_table_exists.return_value = {
        "exists": False,
        "error": "Table 'invalid_table' not found",
        "available_tables": ["table1", "table2"],
        "suggestion": "table1"
    }
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await add_grist_records_safe(doc_id, table_id, records, mock_ctx)
    
    # Vérifications
    assert result["success"] is False
    assert "Table 'invalid_table' not found" in result["message"]
    assert "available_tables" in result
    assert "suggestion" in result
    assert result["suggestion"] == "table1"


@pytest.mark.asyncio
async def test_update_grist_records(mock_grist_client, mock_ctx):
    """Teste l'outil update_grist_records."""
    # Données d'entrée
    doc_id = "doc1"
    table_id = "table1"
    records = [
        {"id": 1, "name": "Updated 1", "value": 150},
        {"id": 2, "name": "Updated 2", "value": 250}
    ]
    
    # Configuration du mock
    mock_grist_client.update_records.return_value = [1, 2]
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await update_grist_records(doc_id, table_id, records, mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "2 enregistrements mis à jour" in result["message"]
    assert result["record_ids"] == [1, 2]
    
    # Vérifier que la méthode a été appelée avec les bons paramètres
    mock_grist_client.update_records.assert_called_once_with(doc_id, table_id, records)


@pytest.mark.asyncio
async def test_update_grist_records_missing_id(mock_grist_client, mock_ctx):
    """Teste update_grist_records avec un enregistrement sans ID."""
    # Données d'entrée avec un enregistrement sans ID
    doc_id = "doc1"
    table_id = "table1"
    records = [
        {"id": 1, "name": "Updated 1"},
        {"name": "Missing ID"}  # Pas d'ID
    ]
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await update_grist_records(doc_id, table_id, records, mock_ctx)
    
    # Vérifications
    assert result["success"] is False
    assert "n'a pas d'ID" in result["message"]
    assert result["record_ids"] == []
    
    # Vérifier que la méthode n'a pas été appelée
    mock_grist_client.update_records.assert_not_called()


@pytest.mark.asyncio
async def test_delete_grist_records(mock_grist_client, mock_ctx):
    """Teste l'outil delete_grist_records."""
    # Données d'entrée
    doc_id = "doc1"
    table_id = "table1"
    record_ids = [1, 2, 3]
    
    # Configuration du mock
    mock_grist_client.delete_records.return_value = None
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await delete_grist_records(doc_id, table_id, record_ids, mock_ctx)
    
    # Vérifications
    assert result["success"] is True
    assert "3 enregistrements supprimés" in result["message"]
    
    # Vérifier que la méthode a été appelée avec les bons paramètres
    mock_grist_client.delete_records.assert_called_once_with(doc_id, table_id, record_ids)


@pytest.mark.asyncio
async def test_delete_grist_records_invalid_id(mock_grist_client, mock_ctx):
    """Teste delete_grist_records avec un ID invalide."""
    # Données d'entrée avec un ID non entier
    doc_id = "doc1"
    table_id = "table1"
    record_ids = [1, "invalid", 3]
    
    # Patch la fonction get_client pour retourner notre mock
    with patch("mcp_server_grist.tools.records.get_client", return_value=mock_grist_client):
        result = await delete_grist_records(doc_id, table_id, record_ids, mock_ctx)
    
    # Vérifications
    assert result["success"] is False
    assert "n'est pas un entier" in result["message"]
    
    # Vérifier que la méthode n'a pas été appelée
    mock_grist_client.delete_records.assert_not_called()
