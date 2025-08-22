"""
Tests de sécurité pour le MCP Server Grist.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import sys

# Ajouter le répertoire parent au chemin pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import grist_mcp_server

class TestSecurity(unittest.TestCase):
    """Tests de sécurité pour le MCP Server Grist."""

    def test_mask_api_key(self):
        """Teste la fonction de masquage des clés API."""
        # Test avec une clé API longue
        long_key = "abcdefghijklmnopqrstuvwxyz123456"
        masked_long = grist_mcp_server.mask_api_key(long_key)
        self.assertEqual(masked_long, "abcde...23456")
        
        # Test avec une clé API courte
        short_key = "abc123"
        masked_short = grist_mcp_server.mask_api_key(short_key)
        self.assertEqual(masked_short, "[SET]")
        
        # Test avec une clé API vide
        empty_key = ""
        masked_empty = grist_mcp_server.mask_api_key(empty_key)
        self.assertEqual(masked_empty, "[SET]")

    @patch('grist_mcp_server.GristClient')
    async def test_sql_injection_prevention(self, mock_client):
        """Teste la prévention des injections SQL."""
        # Simuler le contexte et le client
        ctx = MagicMock()
        client = MagicMock()
        ctx.get_value.return_value = client
        
        # Créer une tentative d'injection SQL
        doc_id = "doc1"
        sql_injection = "SELECT * FROM Table1; DROP TABLE Table2; --"
        parameters = []
        
        # Configurer le mock pour simuler une réponse
        client.execute_sql.return_value = {"rows": [], "columns": []}
        
        # Exécuter la fonction avec la tentative d'injection
        result = await grist_mcp_server.execute_sql_query(
            doc_id=doc_id,
            sql_query=sql_injection,
            parameters=parameters,
            ctx=ctx
        )
        
        # Vérifier que le client a été appelé avec les paramètres corrects
        client.execute_sql.assert_called_once()
        
        # Le serveur MCP ne permet que les requêtes SELECT
        # Vérifions qu'un message d'erreur est retourné pour les requêtes non-SELECT
        sql_non_select = "INSERT INTO Table1 VALUES (1, 'test')"
        
        # Réinitialiser le mock
        client.reset_mock()
        
        # Exécuter la fonction avec la requête non-SELECT
        result = await grist_mcp_server.execute_sql_query(
            doc_id=doc_id,
            sql_query=sql_non_select,
            parameters=parameters,
            ctx=ctx
        )
        
        # Vérifier que l'exécution a échoué et retourne un message d'erreur approprié
        self.assertEqual(result["success"], False)
        self.assertIn("requête non autorisée", result["message"].lower())

    @patch('grist_mcp_server.GristClient')
    async def test_authentication_required(self, mock_client):
        """Teste que l'authentification est requise pour toutes les opérations."""
        # Simuler le contexte sans client configuré (pas de clé API)
        ctx = MagicMock()
        ctx.get_value.return_value = None
        
        # Tenter d'exécuter l'outil list_organizations
        result = await grist_mcp_server.list_organizations(ctx)
        
        # Vérifier que l'opération a échoué avec un message d'erreur approprié
        self.assertEqual(result["success"], False)
        self.assertIn("client non configuré", result["message"].lower())

if __name__ == '__main__':
    unittest.main()
