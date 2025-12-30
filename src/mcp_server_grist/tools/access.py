"""
Outils de gestion des accès pour l'API Grist.

Ce module contient des outils MCP pour gérer les droits d'accès
aux organisations, espaces de travail et documents Grist.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context

from ..client import get_client

# Configurer le logger
logger = logging.getLogger("grist_mcp_server")


def register_access_tools(mcp_server):
    """
    Enregistre tous les outils de gestion des accès sur le serveur MCP.
    
    Args:
        mcp_server: L'instance du serveur MCP sur laquelle enregistrer les outils.
    """
    # Organisation
    mcp_server.tool()(list_organization_access)
    mcp_server.tool()(modify_organization_access)
    
    # Workspace
    mcp_server.tool()(list_workspace_access)
    mcp_server.tool()(modify_workspace_access)
    
    # Document
    mcp_server.tool()(list_document_access)
    mcp_server.tool()(modify_document_access)


# --- Organisation Access ---

async def list_organization_access(
    org_id: Union[int, str],
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Liste les utilisateurs ayant accès à une organisation.
    
    Prérequis:
        - list_organizations: Pour obtenir un org_id valide
    
    Args:
        org_id: L'ID de l'organisation
        
    Returns:
        Dict avec statut, message et détails des accès
    """
    logger.info(f"Tool called: list_organization_access with org_id: {org_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        access_info = await client.list_org_access(org_id)
        
        return {
            "success": True,
            "message": f"Accès à l'organisation {org_id} récupérés avec succès",
            "access": access_info
        }
    except Exception as e:
        logger.error(f"Error listing organization access: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la récupération des accès à l'organisation: {str(e)}"
        }


async def modify_organization_access(
    org_id: Union[int, str],
    user_email: str,
    access_level: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modifie l'accès d'un utilisateur à une organisation.
    
    Prérequis:
        - list_organizations: Pour obtenir un org_id valide
        - list_organization_access: Pour voir les accès actuels
    
    Args:
        org_id: L'ID de l'organisation
        user_email: Email de l'utilisateur
        access_level: Niveau d'accès (owners, editors, viewers, members, ou null pour supprimer)
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: modify_organization_access with org_id: {org_id}, user_email: {user_email}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        if access_level not in ["owners", "editors", "viewers", "members", "null"]:
            return {
                "success": False,
                "message": "Niveau d'accès invalide. Doit être: owners, editors, viewers, members, ou null"
            }
        
        access_delta = {
            "users": {
                user_email: None if access_level == "null" else access_level
            }
        }
        
        await client.modify_org_access(org_id, access_delta)
        
        action = "supprimé" if access_level == "null" else f"défini à {access_level}"
        return {
            "success": True,
            "message": f"Accès pour {user_email} {action} avec succès"
        }
    except Exception as e:
        logger.error(f"Error modifying organization access: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la modification des accès à l'organisation: {str(e)}"
        }


# --- Workspace Access ---

async def list_workspace_access(
    workspace_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Liste les utilisateurs ayant accès à un espace de travail.
    
    Prérequis:
        - list_workspaces: Pour obtenir un workspace_id valide
    
    Args:
        workspace_id: L'ID de l'espace de travail
        
    Returns:
        Dict avec statut, message et détails des accès
    """
    logger.info(f"Tool called: list_workspace_access with workspace_id: {workspace_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        access_info = await client.list_workspace_access(workspace_id)
        
        return {
            "success": True,
            "message": f"Accès à l'espace de travail {workspace_id} récupérés avec succès",
            "access": access_info
        }
    except Exception as e:
        logger.error(f"Error listing workspace access: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la récupération des accès à l'espace de travail: {str(e)}"
        }


async def modify_workspace_access(
    workspace_id: int,
    user_email: str,
    access_level: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modifie l'accès d'un utilisateur à un espace de travail.
    
    Prérequis:
        - list_workspaces: Pour obtenir un workspace_id valide
        - list_workspace_access: Pour voir les accès actuels
    
    Args:
        workspace_id: L'ID de l'espace de travail
        user_email: Email de l'utilisateur
        access_level: Niveau d'accès (owners, editors, viewers, ou null pour supprimer)
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: modify_workspace_access with workspace_id: {workspace_id}, user_email: {user_email}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        if access_level not in ["owners", "editors", "viewers", "null"]:
            return {
                "success": False,
                "message": "Niveau d'accès invalide. Doit être: owners, editors, viewers, ou null"
            }
        
        access_delta = {
            "users": {
                user_email: None if access_level == "null" else access_level
            }
        }
        
        await client.modify_workspace_access(workspace_id, access_delta)
        
        action = "supprimé" if access_level == "null" else f"défini à {access_level}"
        return {
            "success": True,
            "message": f"Accès pour {user_email} {action} avec succès"
        }
    except Exception as e:
        logger.error(f"Error modifying workspace access: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la modification des accès à l'espace de travail: {str(e)}"
        }


# --- Document Access ---

async def list_document_access(
    doc_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Liste les utilisateurs ayant accès à un document.
    
    Prérequis:
        - list_documents: Pour obtenir un doc_id valide
    
    Args:
        doc_id: L'ID du document
        
    Returns:
        Dict avec statut, message et détails des accès
    """
    logger.info(f"Tool called: list_document_access with doc_id: {doc_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        access_info = await client.list_doc_access(doc_id)
        
        return {
            "success": True,
            "message": f"Accès au document {doc_id} récupérés avec succès",
            "access": access_info
        }
    except Exception as e:
        logger.error(f"Error listing document access: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la récupération des accès au document: {str(e)}"
        }


async def modify_document_access(
    doc_id: str,
    user_email: str,
    access_level: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modifie l'accès d'un utilisateur à un document.
    
    Prérequis:
        - list_documents: Pour obtenir un doc_id valide
        - list_document_access: Pour voir les accès actuels
    
    Args:
        doc_id: L'ID du document
        user_email: Email de l'utilisateur
        access_level: Niveau d'accès (owners, editors, viewers, ou null pour supprimer)
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: modify_document_access with doc_id: {doc_id}, user_email: {user_email}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        if access_level not in ["owners", "editors", "viewers", "null"]:
            return {
                "success": False,
                "message": "Niveau d'accès invalide. Doit être: owners, editors, viewers, ou null"
            }
        
        access_delta = {
            "users": {
                user_email: None if access_level == "null" else access_level
            }
        }
        
        await client.modify_doc_access(doc_id, access_delta)
        
        action = "supprimé" if access_level == "null" else f"défini à {access_level}"
        return {
            "success": True,
            "message": f"Accès pour {user_email} {action} avec succès"
        }
    except Exception as e:
        logger.error(f"Error modifying document access: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la modification des accès au document: {str(e)}"
        }
