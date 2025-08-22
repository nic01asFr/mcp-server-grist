"""
Tests d'intégration pour le MCP Server Grist.

Ces tests nécessitent une instance Grist réelle et une clé API valide.
Pour exécuter ces tests, vous devez définir la variable d'environnement GRIST_API_KEY.

Note: Ces tests sont marqués comme "optionnels" car ils nécessitent une configuration externe.
"""
import os
import unittest
import sys
import json
import pytest
import asyncio

# Ajouter le répertoire parent au chemin pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grist_mcp_server import (
    GristClient,
    list_organizations,
    list_workspaces,
    list_documents,
    list_tables,
    list_columns,
    list_records,
    add_grist_records,
    update_grist_records,
    delete_grist_records
)
from fastmcp import Context

class TestIntegration(unittest.TestCase):
    """Tests d'intégration pour le MCP Server Grist."""
    
    @classmethod
    def setUpClass(cls):
        """Configuration avant tous les tests."""
        # Vérifier si les variables d'environnement nécessaires sont définies
        cls.api_key = os.environ.get("GRIST_API_KEY")
        cls.api_url = os.environ.get("GRIST_API_HOST", "https://docs.getgrist.com/api")
        
        # Si la clé API n'est pas définie, marquer tous les tests comme ignorés
        if not cls.api_key:
            pytest.skip("GRIST_API_KEY non définie. Tests d'intégration ignorés.", allow_module_level=True)
        
        # Créer une instance du client Grist
        cls.client = GristClient(cls.api_key, cls.api_url)
        
        # Créer un contexte MCP simulé
        cls.ctx = Context()
        cls.ctx.set_value("grist_client", cls.client)
        
        # Variables pour stocker les IDs pour les tests
        cls.test_data = {}
    
    async def test_01_list_organizations(self):
        """Teste l'outil list_organizations avec une API réelle."""
        # Exécuter l'outil
        result = await list_organizations(self.ctx)
        
        # Vérifications
        self.assertEqual(result["success"], True)
        self.assertIsInstance(result["organizations"], list)
        
        # Si des organisations existent, stocker le premier ID pour les tests suivants
        if result["organizations"]:
            self.__class__.test_data["org_id"] = result["organizations"][0]["id"]
            print(f"Organisation ID pour les tests: {self.__class__.test_data['org_id']}")
    
    async def test_02_list_workspaces(self):
        """Teste l'outil list_workspaces avec une API réelle."""
        # Vérifier si un org_id a été trouvé dans le test précédent
        if "org_id" not in self.__class__.test_data:
            self.skipTest("Aucune organisation trouvée pour le test")
        
        # Exécuter l'outil
        result = await list_workspaces(self.__class__.test_data["org_id"], self.ctx)
        
        # Vérifications
        self.assertEqual(result["success"], True)
        self.assertIsInstance(result["workspaces"], list)
        
        # Si des workspaces existent, stocker le premier ID pour les tests suivants
        if result["workspaces"]:
            self.__class__.test_data["workspace_id"] = result["workspaces"][0]["id"]
            print(f"Workspace ID pour les tests: {self.__class__.test_data['workspace_id']}")
    
    async def test_03_list_documents(self):
        """Teste l'outil list_documents avec une API réelle."""
        # Vérifier si un workspace_id a été trouvé dans le test précédent
        if "workspace_id" not in self.__class__.test_data:
            self.skipTest("Aucun workspace trouvé pour le test")
        
        # Exécuter l'outil
        result = await list_documents(self.__class__.test_data["workspace_id"], self.ctx)
        
        # Vérifications
        self.assertEqual(result["success"], True)
        self.assertIsInstance(result["documents"], list)
        
        # Si des documents existent, stocker le premier ID pour les tests suivants
        if result["documents"]:
            self.__class__.test_data["doc_id"] = result["documents"][0]["id"]
            print(f"Document ID pour les tests: {self.__class__.test_data['doc_id']}")
    
    async def test_04_list_tables(self):
        """Teste l'outil list_tables avec une API réelle."""
        # Vérifier si un doc_id a été trouvé dans le test précédent
        if "doc_id" not in self.__class__.test_data:
            self.skipTest("Aucun document trouvé pour le test")
        
        # Exécuter l'outil
        result = await list_tables(self.__class__.test_data["doc_id"], self.ctx)
        
        # Vérifications
        self.assertEqual(result["success"], True)
        self.assertIsInstance(result["tables"], list)
        
        # Si des tables existent, stocker le premier ID pour les tests suivants
        if result["tables"]:
            self.__class__.test_data["table_id"] = result["tables"][0]["id"]
            print(f"Table ID pour les tests: {self.__class__.test_data['table_id']}")
    
    async def test_05_list_columns(self):
        """Teste l'outil list_columns avec une API réelle."""
        # Vérifier si les IDs nécessaires ont été trouvés dans les tests précédents
        if "doc_id" not in self.__class__.test_data or "table_id" not in self.__class__.test_data:
            self.skipTest("Aucun document ou table trouvé pour le test")
        
        # Exécuter l'outil
        result = await list_columns(
            self.__class__.test_data["doc_id"],
            self.__class__.test_data["table_id"],
            self.ctx
        )
        
        # Vérifications
        self.assertEqual(result["success"], True)
        self.assertIsInstance(result["columns"], list)
        
        # Stocker les colonnes pour les tests suivants
        if result["columns"]:
            self.__class__.test_data["columns"] = result["columns"]
            print(f"Colonnes trouvées: {len(self.__class__.test_data['columns'])}")

    # Note: Les tests suivants pour add/update/delete sont commentés car ils modifieraient les données
    # Ils devraient être exécutés uniquement dans un environnement de test dédié
    
    """
    async def test_06_add_records(self):
        #Teste l outil add_grist_records avec une API réelle.
        # Vérifier si les IDs nécessaires ont été trouvés dans les tests précédents
        if ("doc_id" not in self.__class__.test_data or 
            "table_id" not in self.__class__.test_data or
            "columns" not in self.__class__.test_data):
            self.skipTest("Informations nécessaires non trouvées pour le test")
        
        # Créer un enregistrement de test basé sur les colonnes disponibles
        test_record = {}
        for column in self.__class__.test_data["columns"]:
            col_id = column["id"]
            col_type = column.get("fields", {}).get("type", "Text")
            
            # Remplir avec des valeurs de test selon le type
            if col_type == "Text":
                test_record[col_id] = "Test Value"
            elif col_type == "Numeric" or col_type == "Int":
                test_record[col_id] = 42
            elif col_type == "Bool":
                test_record[col_id] = True
            # Ignorer les autres types pour simplifier le test
        
        # Exécuter l'outil
        result = await add_grist_records(
            self.__class__.test_data["doc_id"],
            self.__class__.test_data["table_id"],
            [test_record],
            self.ctx
        )
        
        # Vérifications
        self.assertEqual(result["success"], True)
        self.assertIsInstance(result["record_ids"], list)
        
        # Stocker l'ID de l'enregistrement pour les tests suivants
        if result["record_ids"]:
            self.__class__.test_data["record_id"] = result["record_ids"][0]
            print(f"Record ID créé: {self.__class__.test_data['record_id']}")
    """

def run_test(test_name):
    """Exécute un test spécifique de manière asynchrone."""
    test = TestIntegration(test_name)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(getattr(test, test_name)())

if __name__ == '__main__':
    # Exécuter les tests en séquence dans le bon ordre
    tests = [
        'test_01_list_organizations',
        'test_02_list_workspaces',
        'test_03_list_documents',
        'test_04_list_tables',
        'test_05_list_columns',
        # 'test_06_add_records',  # Commenté pour éviter de modifier les données
    ]
    
    for test in tests:
        print(f"\nExécution du test: {test}")
        try:
            run_test(test)
            print("✅ Test réussi")
        except Exception as e:
            print(f"❌ Test échoué: {str(e)}")
