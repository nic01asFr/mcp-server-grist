"""
Outils de gestion des webhooks pour l'API Grist.

Ce module contient des outils MCP pour gérer les webhooks
dans les documents Grist: liste, création, modification, suppression.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context

from ..client import get_client

# Configurer le logger
logger = logging.getLogger("grist_mcp_server")


def register_webhook_tools(mcp_server):
    """
    Enregistre tous les outils de gestion des webhooks sur le serveur MCP.
    
    Args:
        mcp_server: L'instance du serveur MCP sur laquelle enregistrer les outils.
    """
    mcp_server.tool()(list_webhooks)
    mcp_server.tool()(create_webhook)
    mcp_server.tool()(modify_webhook)
    mcp_server.tool()(delete_webhook)
    mcp_server.tool()(clear_webhook_queue)


async def list_webhooks(doc_id: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Liste les webhooks d'un document Grist.
    
    Prérequis:
        - list_documents: Pour obtenir un doc_id valide
    
    Args:
        doc_id: L'ID du document
        
    Returns:
        Dict avec statut, message et liste des webhooks
    """
    logger.info(f"Tool called: list_webhooks with doc_id: {doc_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré",
                "webhooks": []
            }
        
        webhooks = await client.list_webhooks(doc_id)
        
        return {
            "success": True,
            "message": f"{len(webhooks)} webhooks trouvés dans le document {doc_id}",
            "webhooks": webhooks
        }
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la récupération des webhooks pour le document {doc_id}: {str(e)}",
            "webhooks": []
        }


async def create_webhook(
    doc_id: str,
    url: str,
    table_id: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    memo: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Crée un webhook pour un document Grist.
    
    Prérequis:
        - list_documents: Pour obtenir un doc_id valide
        - list_tables: Pour obtenir un table_id valide (si spécifié)
    
    Args:
        doc_id: L'ID du document
        url: URL du webhook (où les notifications seront envoyées)
        table_id: ID de la table à surveiller (optionnel, tous si non spécifié)
        event_types: Types d'événements à surveiller (optionnel, tous si non spécifié)
                    Valeurs possibles: ["add", "update", "delete"]
        memo: Note descriptive pour le webhook (optionnel)
        
    Returns:
        Dict avec statut, message et ID du webhook créé
    """
    logger.info(f"Tool called: create_webhook with doc_id: {doc_id}, url: {url}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        # Valider les types d'événements
        valid_event_types = ["add", "update", "delete"]
        if event_types:
            for event_type in event_types:
                if event_type not in valid_event_types:
                    return {
                        "success": False,
                        "message": f"Type d'événement invalide: {event_type}. Doit être parmi: {valid_event_types}"
                    }
        
        # Préparer les données du webhook
        webhook_data = {
            "url": url
        }
        
        if table_id:
            webhook_data["tableId"] = table_id
        
        if event_types:
            webhook_data["eventTypes"] = event_types
        
        if memo:
            webhook_data["memo"] = memo
        
        # Créer le webhook
        result = await client.create_webhooks(doc_id, [webhook_data])
        
        if result and len(result) > 0:
            webhook_id = result[0].get("id")
            return {
                "success": True,
                "message": f"Webhook créé avec succès pour l'URL {url}",
                "webhook_id": webhook_id,
                "webhook": result[0]
            }
        else:
            return {
                "success": False,
                "message": "Aucun webhook n'a été créé"
            }
    except Exception as e:
        logger.error(f"Error creating webhook: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la création du webhook: {str(e)}"
        }


async def modify_webhook(
    doc_id: str,
    webhook_id: str,
    url: Optional[str] = None,
    table_id: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    memo: Optional[str] = None,
    active: Optional[bool] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modifie un webhook existant.
    
    Prérequis:
        - list_webhooks: Pour obtenir un webhook_id valide
    
    Args:
        doc_id: L'ID du document
        webhook_id: L'ID du webhook à modifier
        url: Nouvelle URL du webhook (optionnel)
        table_id: Nouvel ID de table à surveiller (optionnel)
        event_types: Nouveaux types d'événements à surveiller (optionnel)
        memo: Nouvelle note descriptive (optionnel)
        active: État d'activation du webhook (optionnel)
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: modify_webhook with doc_id: {doc_id}, webhook_id: {webhook_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        # Valider les types d'événements
        valid_event_types = ["add", "update", "delete"]
        if event_types:
            for event_type in event_types:
                if event_type not in valid_event_types:
                    return {
                        "success": False,
                        "message": f"Type d'événement invalide: {event_type}. Doit être parmi: {valid_event_types}"
                    }
        
        # Préparer les données de modification
        webhook_data = {}
        
        if url is not None:
            webhook_data["url"] = url
        
        if table_id is not None:
            webhook_data["tableId"] = table_id
        
        if event_types is not None:
            webhook_data["eventTypes"] = event_types
        
        if memo is not None:
            webhook_data["memo"] = memo
        
        if active is not None:
            webhook_data["active"] = active
        
        if not webhook_data:
            return {
                "success": False,
                "message": "Aucune donnée de modification fournie"
            }
        
        # Modifier le webhook
        await client.modify_webhook(doc_id, webhook_id, webhook_data)
        
        return {
            "success": True,
            "message": f"Webhook {webhook_id} modifié avec succès"
        }
    except Exception as e:
        logger.error(f"Error modifying webhook: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la modification du webhook: {str(e)}"
        }


async def delete_webhook(
    doc_id: str,
    webhook_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Supprime un webhook.
    
    Prérequis:
        - list_webhooks: Pour obtenir un webhook_id valide
    
    Args:
        doc_id: L'ID du document
        webhook_id: L'ID du webhook à supprimer
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: delete_webhook with doc_id: {doc_id}, webhook_id: {webhook_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        result = await client.delete_webhook(doc_id, webhook_id)
        
        return {
            "success": True,
            "message": f"Webhook {webhook_id} supprimé avec succès"
        }
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la suppression du webhook: {str(e)}"
        }


async def clear_webhook_queue(
    doc_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Vide la file d'attente des webhooks pour un document.
    
    Utile en cas d'accumulation de notifications non envoyées.
    
    Args:
        doc_id: L'ID du document
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: clear_webhook_queue with doc_id: {doc_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        await client.clear_webhook_queue(doc_id)
        
        return {
            "success": True,
            "message": f"File d'attente des webhooks vidée avec succès pour le document {doc_id}"
        }
    except Exception as e:
        logger.error(f"Error clearing webhook queue: {e}")
        return {
            "success": False,
            "message": f"Erreur lors du vidage de la file d'attente des webhooks: {str(e)}"
        }
