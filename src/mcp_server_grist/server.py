"""
Configuration et gestion du serveur MCP pour Grist.

Ce module configure et initialise le serveur MCP avec les outils
appropriés pour interagir avec l'API Grist.
"""

import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

from .tools import register_all_tools
from .version import __version__

# Configurer le logger
logger = logging.getLogger("grist_mcp_server")


def init_logging(debug: bool = False):
    """
    Initialise la configuration de logging.
    
    Args:
        debug: Si True, active le niveau de log DEBUG.
    """
    load_dotenv()
    
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    if debug:
        log_level = logging.DEBUG
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Réduire la verbosité des logs de bibliothèques externes
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def create_mcp_server(debug: bool = False, parameters: Optional[Dict[str, str]] = None) -> FastMCP:
    """
    Crée et configure une instance du serveur MCP.
    
    Args:
        debug: Si True, active le mode debug.
        parameters: Paramètres MCP fournis par Claude Desktop
        
    Returns:
        L'instance configurée du serveur MCP.
    """
    # Initialiser le logging
    init_logging(debug)
    
    # Vérifier la présence de la clé API Grist
    load_dotenv()
    
    # Priorité aux paramètres MCP fournis par Claude Desktop
    if parameters and "GRIST_API_KEY" in parameters:
        os.environ["GRIST_API_KEY"] = parameters["GRIST_API_KEY"]
    
    if parameters and "GRIST_API_URL" in parameters:
        os.environ["GRIST_API_URL"] = parameters["GRIST_API_URL"]
    
    api_key = os.environ.get("GRIST_API_KEY")
    
    if not api_key:
        logger.warning(
            "GRIST_API_KEY n'est pas définie. "
            "Définissez-la dans le fichier .env, comme variable d'environnement, "
            "ou dans la configuration MCP de Claude Desktop."
        )
    
    # Configurer le serveur MCP
    mcp = FastMCP(
        name="GristMCP",
        version=__version__
    )
    
    # Les versions récentes de FastMCP n'utilisent plus set_system_message
    # Nous gardons les instructions pour référence
    # get_mcp_instructions()
    
    # Enregistrer tous les outils sur le serveur
    register_all_tools(mcp)
    
    logger.info(f"Serveur MCP Grist v{__version__} initialisé")
    return mcp


def get_mcp_instructions() -> str:
    """
    Retourne les instructions système pour les modèles utilisant le serveur MCP.
    
    Returns:
        Instructions système formatées.
    """
    return """
# Serveur MCP Grist

Ce serveur MCP vous permet d'interagir avec l'API Grist pour accéder aux données 
et effectuer des actions sur des documents Grist.

## Architecture hiérarchique

L'API Grist s'organise de façon hiérarchique:
1. Organisation
2. Workspace (espace de travail)
3. Document
4. Table
5. Colonne
6. Enregistrement (record)

## Flux de travail essentiels

Pour explorer les données:
1. `list_organizations()` → obtenir un org_id
2. `list_workspaces(org_id)` → obtenir un workspace_id
3. `list_documents(workspace_id)` → obtenir un doc_id
4. `list_tables(doc_id)` → obtenir un table_id
5. `list_columns(doc_id, table_id)` → voir la structure
6. `list_records(doc_id, table_id)` → accéder aux données

Pour modifier des données:
1. Explorer la structure (comme ci-dessus)
2. `add_grist_records(doc_id, table_id, records)` → ajouter
3. `update_grist_records(doc_id, table_id, records)` → modifier
4. `delete_grist_records(doc_id, table_id, record_ids)` → supprimer

Pour des requêtes avancées:
- `filter_sql_query(doc_id, table_id, where_conditions={"status": "actif"})` → filtrer
- `execute_sql_query(doc_id, "SELECT * FROM Table1 WHERE status = ?", ["actif"])` → SQL

## Catégories d'outils

1. **Navigation** - explorer la structure
2. **Records** - manipuler les enregistrements
3. **Queries** - exécuter des requêtes SQL
4. **Administration** - gérer les objets (workspaces, docs, etc.)
5. **Attachments** - gérer les pièces jointes
6. **Webhooks** - gérer les webhooks Grist

## Important

- Toutes les opérations nécessitent un `doc_id` valide
- Les valeurs d'ID sont sensibles à la casse
- Pour les nouveaux utilisateurs, commencez par `list_organizations()`
- Utilisez les outils "safe" pour une validation supplémentaire
- Les erreurs incluent souvent des suggestions utiles
    """