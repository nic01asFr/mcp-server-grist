"""
Module d'intégration des outils supplémentaires au MCP Grist Server.
"""

import sys
import logging
from typing import Dict, Any

# Configuration du logging
logger = logging.getLogger("grist_tools_integration")

def register_all_tools(mcp_server, get_client_func):
    """
    Enregistre tous les outils supplémentaires auprès du MCP Server.
    
    Args:
        mcp_server: Instance du serveur FastMCP
        get_client_func: Fonction pour obtenir un client Grist configuré
    
    Returns:
        Informations sur les outils enregistrés
    """
    logger.info("Initialisation de l'intégration des outils supplémentaires pour Grist")
    
    try:
        # Import dynamique des outils supplémentaires
        from grist_additional_tools import register_additional_tools
        
        # Enregistrement des outils
        tools = register_additional_tools(mcp_server, get_client_func)
        
        # Compter les outils
        tool_count = len(tools)
        
        logger.info(f"{tool_count} outils supplémentaires enregistrés avec succès")
        
        return {
            "success": True,
            "message": f"{tool_count} outils supplémentaires enregistrés",
            "tools": list(tools.keys())
        }
    except ImportError as e:
        logger.error(f"Erreur d'importation du module d'outils supplémentaires: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de l'importation du module: {str(e)}",
            "error_type": "ImportError"
        }
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'initialisation des outils supplémentaires: {e}")
        return {
            "success": False,
            "message": f"Erreur inattendue: {str(e)}",
            "error_type": type(e).__name__
        }
