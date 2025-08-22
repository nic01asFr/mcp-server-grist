"""
Outils MCP pour l'API Grist.

Ce module regroupe tous les outils MCP disponibles pour interagir
avec l'API Grist, organisés par catégories fonctionnelles.
"""

from .access import register_access_tools
from .administration import register_admin_tools
from .attachments import register_attachment_tools
from .export import register_export_tools
from .navigation import register_navigation_tools
from .queries import register_query_tools
from .records import register_record_tools
from .webhooks import register_webhook_tools


def register_all_tools(mcp_server):
    """
    Enregistre tous les outils MCP disponibles sur le serveur.
    
    Cette fonction centralise l'enregistrement de tous les outils
    pour faciliter leur gestion et leur découverte.
    
    Args:
        mcp_server: L'instance du serveur MCP sur laquelle enregistrer les outils.
    """
    # Navigation (lecture)
    register_navigation_tools(mcp_server)
    
    # Records (écriture)
    register_record_tools(mcp_server)
    
    # Queries (requêtes SQL)
    register_query_tools(mcp_server)
    
    # Administration
    register_admin_tools(mcp_server)
    
    # Gestion des accès
    register_access_tools(mcp_server)
    
    # Export et téléchargement
    register_export_tools(mcp_server)
    
    # Pièces jointes
    register_attachment_tools(mcp_server)
    
    # Webhooks
    register_webhook_tools(mcp_server)