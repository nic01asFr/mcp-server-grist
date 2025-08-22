"""
Tests pour les transports MCP.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import sys
import argparse

# Ajouter le répertoire parent au chemin pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import grist_mcp_server

class TestTransport(unittest.TestCase):
    """Tests pour la gestion des transports MCP."""
    
    def test_stdio_transport(self):
        """Teste la configuration du transport stdio."""
        # Vérifier que le code principal supporte le transport stdio
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'grist_mcp_server.py'), 'r') as f:
            content = f.read()
            # Vérifier que le transport stdio est mentionné et supporté
            self.assertIn('transport="stdio"', content)
            self.assertIn('if args.transport == "stdio"', content)

    def test_streamable_http_transport(self):
        """Teste la configuration du transport streamable-http."""
        # Vérifier que le code principal supporte le transport streamable-http
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'grist_mcp_server.py'), 'r') as f:
            content = f.read()
            # Vérifier que le transport streamable-http est mentionné et supporté
            self.assertIn('transport="streamable-http"', content)
            self.assertIn('elif args.transport == "streamable-http"', content)
            # Vérifier que les paramètres de configuration sont présents
            self.assertIn('host=args.host', content)
            self.assertIn('port=args.port', content)

    def test_sse_transport(self):
        """Teste la configuration du transport SSE."""
        # Vérifier que le code principal supporte le transport SSE
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'grist_mcp_server.py'), 'r') as f:
            content = f.read()
            # Vérifier que le transport SSE est mentionné et supporté
            self.assertIn('transport="sse"', content)
            self.assertIn('elif args.transport == "sse"', content)
            # Vérifier que le transport SSE est inclus dans les choix possibles
            self.assertIn('"stdio", "streamable-http", "sse"', content)

    def test_api_key_check(self):
        """Teste la vérification de la clé API."""
        # Vérifier que le code principal vérifie bien la clé API
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'grist_mcp_server.py'), 'r') as f:
            content = f.read()
            # Vérifier que la vérification de la clé API est présente
            self.assertIn('api_key = os.environ.get("GRIST_API_KEY")', content)
            self.assertIn('if not api_key:', content)
            # Vérifier qu'il y a bien un exit en cas d'absence de clé API
            self.assertIn('sys.exit(1)', content)

if __name__ == '__main__':
    unittest.main()
