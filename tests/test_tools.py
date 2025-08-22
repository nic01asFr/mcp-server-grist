"""
Tests pour les outils MCP Grist.
"""
import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import sys

# Ajouter le répertoire parent au chemin pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des fonctions à tester
from grist_mcp_server import (
    list_organizations, 
    list_workspaces, 
    list_documents,
    list_tables,
    list_columns,
    list_records,
    add_grist_records,
    update_grist_records,
    delete_grist_records,
    filter_sql_query,
    execute_sql_query
)

class TestMCPTools(unittest.TestCase):
    """Tests unitaires pour les outils MCP."""

    def setUp(self):
        """Configuration avant chaque test."""
        # Mock pour le contexte MCP
        self.ctx = MagicMock()
        # Mock pour le client Grist (simulé)
        self.client_mock = MagicMock()
        self.ctx.get_value.return_value = self.client_mock

    @patch('grist_mcp_server.GristClient')
    async def test_list_organizations(self, mock_client_class):
        """Teste l'outil list_organizations."""
        # Configurer le mock
        mock_orgs = [{"id": 1, "name": "TestOrg"}]
        self.client_mock.list_organizations.return_value = mock_orgs
        
        # Exécuter l'outil
        result = await list_organizations(self.ctx)
        
        # Vérifications
        self.client_mock.list_organizations.assert_called_once()
        self.assertEqual(result["success"], True)
        self.assertEqual(result["organizations"], mock_orgs)

    @patch('grist_mcp_server.GristClient')
    async def test_list_workspaces(self, mock_client_class):
        """Teste l'outil list_workspaces."""
        # Configurer le mock
        org_id = 1
        mock_workspaces = [{"id": 1, "name": "TestWorkspace"}]
        self.client_mock.list_workspaces.return_value = mock_workspaces
        
        # Exécuter l'outil
        result = await list_workspaces(org_id, self.ctx)
        
        # Vérifications
        self.client_mock.list_workspaces.assert_called_once_with(org_id)
        self.assertEqual(result["success"], True)
        self.assertEqual(result["workspaces"], mock_workspaces)

    @patch('grist_mcp_server.GristClient')
    async def test_list_documents(self, mock_client_class):
        """Teste l'outil list_documents."""
        # Configurer le mock
        workspace_id = 1
        mock_documents = [{"id": "doc1", "name": "TestDoc"}]
        self.client_mock.list_documents.return_value = mock_documents
        
        # Exécuter l'outil
        result = await list_documents(workspace_id, self.ctx)
        
        # Vérifications
        self.client_mock.list_documents.assert_called_once_with(workspace_id)
        self.assertEqual(result["success"], True)
        self.assertEqual(result["documents"], mock_documents)

    @patch('grist_mcp_server.GristClient')
    async def test_list_tables(self, mock_client_class):
        """Teste l'outil list_tables."""
        # Configurer le mock
        doc_id = "doc1"
        mock_tables = [{"id": "table1", "name": "TestTable"}]
        self.client_mock.list_tables.return_value = mock_tables
        
        # Exécuter l'outil
        result = await list_tables(doc_id, self.ctx)
        
        # Vérifications
        self.client_mock.list_tables.assert_called_once_with(doc_id)
        self.assertEqual(result["success"], True)
        self.assertEqual(result["tables"], mock_tables)

    @patch('grist_mcp_server.GristClient')
    async def test_add_grist_records(self, mock_client_class):
        """Teste l'outil add_grist_records."""
        # Configurer le mock
        doc_id = "doc1"
        table_id = "table1"
        records = [{"name": "Test", "value": 123}]
        record_ids = [1]
        self.client_mock.add_records.return_value = record_ids
        
        # Exécuter l'outil
        result = await add_grist_records(doc_id, table_id, records, self.ctx)
        
        # Vérifications
        self.client_mock.add_records.assert_called_once_with(doc_id, table_id, records)
        self.assertEqual(result["success"], True)
        self.assertEqual(result["record_ids"], record_ids)

    @patch('grist_mcp_server.GristClient')
    async def test_filter_sql_query(self, mock_client_class):
        """Teste l'outil filter_sql_query."""
        # Configurer le mock
        doc_id = "doc1"
        table_id = "table1"
        where_conditions = {"status": "active"}
        mock_records = [{"id": 1, "fields": {"status": "active", "name": "Test"}}]
        
        # Mock de execute_sql_query qui sera appelé par filter_sql_query
        mock_sql_result = {
            "success": True,
            "records": mock_records,
            "record_count": 1,
            "query": "SELECT * FROM table1 WHERE status = ?"
        }
        
        # Patch la fonction execute_sql_query
        with patch('grist_mcp_server.execute_sql_query', AsyncMock(return_value=mock_sql_result)):
            # Exécuter l'outil
            result = await filter_sql_query(
                doc_id=doc_id,
                table_id=table_id,
                where_conditions=where_conditions,
                ctx=self.ctx
            )
            
            # Vérifications
            self.assertEqual(result["success"], True)
            self.assertEqual(result["records"], mock_records)
            self.assertEqual(result["record_count"], 1)

if __name__ == '__main__':
    unittest.main()
