"""
Outils de navigation pour l'API Grist.

Ce module contient des outils MCP pour naviguer dans la structure hiérarchique de Grist:
organisations, espaces de travail, documents, tables, colonnes et enregistrements.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context

from ..client import get_client
from ..models import MCP_Response

# Configurer le logger
logger = logging.getLogger("grist_mcp_server")

def register_navigation_tools(mcp_server):
    """
    Enregistre tous les outils de navigation sur le serveur MCP.
    
    Args:
        mcp_server: L'instance du serveur MCP sur laquelle enregistrer les outils.
    """
    # Enregistrement des outils sur le serveur MCP
    mcp_server.tool()(list_organizations)
    mcp_server.tool()(describe_organization)
    mcp_server.tool()(list_workspaces)
    mcp_server.tool()(describe_workspace)
    mcp_server.tool()(list_documents)
    mcp_server.tool()(describe_document)
    mcp_server.tool()(list_tables)
    mcp_server.tool()(list_columns)
    mcp_server.tool()(list_records)
    mcp_server.tool()(get_table_schema)


async def list_organizations(ctx: Context) -> Dict[str, Any]:
    """
    Liste toutes les organisations Grist accessibles.
    
    Prérequis:
        Aucun - ce tool est le point d'entrée principal pour la navigation.
    
    Flux de travail typique:
        1. list_organizations() → obtenir tous les org_id disponibles
        2. list_workspaces(org_id) → explorer les espaces de travail
    
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - organizations (List): Liste des organisations disponibles
    """
    logger.info("Tool called: list_organizations")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré",
                "organizations": []
            }
        
        orgs = await client.list_orgs()
        
        return {
            "success": True,
            "message": f"Found {len(orgs)} organizations",
            "organizations": [org.model_dump() for org in orgs]
        }
    except Exception as e:
        logger.error(f"Error listing organizations: {e}")
        return {
            "success": False,
            "message": f"Error listing organizations: {str(e)}",
            "organizations": []
        }


async def describe_organization(org_id: Union[int, str], ctx: Context) -> Dict[str, Any]:
    """
    Obtient des informations détaillées sur une organisation spécifique.
    
    Prérequis:
        - list_organizations: Pour obtenir un org_id valide
    
    Flux de travail typique:
        1. list_organizations() → identifier l'organisation
        2. describe_organization(org_id) → obtenir les détails
    
    Args:
        org_id: L'ID de l'organisation à décrire
        
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - organization (Dict): Détails de l'organisation
    """
    logger.info(f"Tool called: describe_organization with org_id: {org_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        org_details = await client.describe_org(org_id)
        
        return {
            "success": True,
            "message": f"Found organization details for {org_id}",
            "organization": org_details
        }
    except Exception as e:
        logger.error(f"Error describing organization: {e}")
        return {
            "success": False,
            "message": f"Error describing organization {org_id}: {str(e)}"
        }


async def list_workspaces(org_id: Union[int, str], ctx: Context) -> Dict[str, Any]:
    """
    Liste tous les espaces de travail dans une organisation Grist.
    
    Prérequis:
        - list_organizations: Pour obtenir un org_id valide
        
    Flux de travail typique:
        1. list_organizations() → choisir org_id
        2. list_workspaces(org_id) → obtenir workspace_id
        3. list_documents(workspace_id) → naviguer dans les documents
    
    Voir aussi:
        - create_workspace: Pour créer un nouvel espace de travail
        - describe_workspace: Pour obtenir les détails d'un workspace
        - modify_workspace_access: Pour gérer les permissions
    
    Args:
        org_id: L'ID de l'organisation (entier ou sous-domaine string)
        
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - workspaces (List): Liste des espaces de travail
    """
    logger.info(f"Tool called: list_workspaces with org_id: {org_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré",
                "workspaces": []
            }
        
        workspaces = await client.list_workspaces(org_id)
        
        return {
            "success": True,
            "message": f"Found {len(workspaces)} workspaces in organization {org_id}",
            "workspaces": [workspace.model_dump() for workspace in workspaces]
        }
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        return {
            "success": False,
            "message": f"Error listing workspaces for organization {org_id}: {str(e)}",
            "workspaces": []
        }


async def describe_workspace(workspace_id: int, ctx: Context) -> Dict[str, Any]:
    """
    Obtient des informations détaillées sur un espace de travail spécifique.
    
    Prérequis:
        - list_workspaces: Pour obtenir un workspace_id valide
    
    Flux de travail typique:
        1. list_organizations() → identifier l'organisation
        2. list_workspaces(org_id) → identifier l'espace de travail
        3. describe_workspace(workspace_id) → obtenir les détails
    
    Args:
        workspace_id: L'ID de l'espace de travail à décrire
        
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - workspace (Dict): Détails de l'espace de travail
    """
    logger.info(f"Tool called: describe_workspace with workspace_id: {workspace_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        workspace_details = await client.describe_workspace(workspace_id)
        
        return {
            "success": True,
            "message": f"Found workspace details for {workspace_id}",
            "workspace": workspace_details
        }
    except Exception as e:
        logger.error(f"Error describing workspace: {e}")
        return {
            "success": False,
            "message": f"Error describing workspace {workspace_id}: {str(e)}"
        }


async def list_documents(workspace_id: int, ctx: Context) -> Dict[str, Any]:
    """
    Liste tous les documents dans un espace de travail Grist.
    
    Prérequis:
        - list_workspaces: Pour obtenir un workspace_id valide
        
    Flux de travail typique:
        1. list_workspaces(org_id) → obtenir workspace_id
        2. list_documents(workspace_id) → obtenir doc_id
        3. list_tables(doc_id) → explorer les tables du document
    
    Voir aussi:
        - create_document: Pour créer un nouveau document
        - describe_document: Pour obtenir les détails d'un document
        - modify_document_access: Pour gérer les permissions
    
    Args:
        workspace_id: L'ID de l'espace de travail
        
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - documents (List): Liste des documents
    """
    logger.info(f"Tool called: list_documents with workspace_id: {workspace_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré",
                "documents": []
            }
        
        documents = await client.list_documents(workspace_id)
        
        return {
            "success": True,
            "message": f"Found {len(documents)} documents in workspace {workspace_id}",
            "documents": [document.model_dump() for document in documents]
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return {
            "success": False,
            "message": f"Error listing documents for workspace {workspace_id}: {str(e)}",
            "documents": []
        }


async def describe_document(doc_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Obtient des informations détaillées sur un document spécifique.
    
    Prérequis:
        - list_documents: Pour obtenir un doc_id valide
    
    Flux de travail typique:
        1. list_documents(workspace_id) → identifier le document
        2. describe_document(doc_id) → obtenir les détails complets
    
    Args:
        doc_id: L'ID du document à décrire
        
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - document (Dict): Détails du document
    """
    logger.info(f"Tool called: describe_document with doc_id: {doc_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        document_details = await client.describe_doc(doc_id)
        
        return {
            "success": True,
            "message": f"Found document details for {doc_id}",
            "document": document_details
        }
    except Exception as e:
        logger.error(f"Error describing document: {e}")
        return {
            "success": False,
            "message": f"Error describing document {doc_id}: {str(e)}"
        }


async def list_tables(doc_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Liste toutes les tables dans un document Grist.
    
    Prérequis:
        - list_documents: Pour obtenir un doc_id valide
        
    Flux de travail typique:
        1. list_documents(workspace_id) → obtenir doc_id
        2. list_tables(doc_id) → obtenir table_id
        3. list_columns(doc_id, table_id) → explorer la structure
    
    Voir aussi:
        - create_table: Pour créer une nouvelle table
        - filter_sql_query: Pour requêter les données d'une table
    
    Args:
        doc_id: L'ID du document
        
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - tables (List): Liste des tables
    """
    logger.info(f"Tool called: list_tables with doc_id: {doc_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré",
                "tables": []
            }
        
        tables = await client.list_tables(doc_id)
        
        return {
            "success": True,
            "message": f"Found {len(tables)} tables in document {doc_id}",
            "tables": [table.model_dump() for table in tables]
        }
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return {
            "success": False,
            "message": f"Error listing tables for document {doc_id}: {str(e)}",
            "tables": []
        }


async def list_columns(doc_id: str, table_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Liste toutes les colonnes dans une table Grist.
    
    Prérequis:
        - list_tables: Pour obtenir un table_id valide
        
    Flux de travail typique:
        1. list_tables(doc_id) → obtenir table_id
        2. list_columns(doc_id, table_id) → explorer la structure
        3. list_records(doc_id, table_id) → obtenir les données
    
    Voir aussi:
        - create_column: Pour ajouter une nouvelle colonne
        - modify_column: Pour modifier une colonne existante
    
    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table
        
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - columns (List): Liste des colonnes
    """
    logger.info(f"Tool called: list_columns with doc_id: {doc_id}, table_id: {table_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré",
                "columns": []
            }
        
        columns = await client.list_columns(doc_id, table_id)
        
        return {
            "success": True,
            "message": f"Found {len(columns)} columns in table {table_id}",
            "columns": [column.model_dump() for column in columns]
        }
    except Exception as e:
        logger.error(f"Error listing columns: {e}")
        return {
            "success": False,
            "message": f"Error listing columns for table {table_id} in document {doc_id}: {str(e)}",
            "columns": []
        }


async def list_records(
    doc_id: str,
    table_id: str,
    sort: Optional[str] = None,
    limit: Optional[int] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Liste les enregistrements dans une table Grist avec tri et limitation optionnels.
    
    Prérequis:
        - list_tables: Pour obtenir un table_id valide
        
    Flux de travail typique:
        1. list_tables(doc_id) → obtenir table_id
        2. list_columns(doc_id, table_id) → comprendre la structure
        3. list_records(doc_id, table_id, sort="nom", limit=10) → obtenir les données
    
    Voir aussi:
        - filter_sql_query: Alternative avec filtrage avancé
        - add_grist_records: Pour ajouter des enregistrements
    
    Args:
        doc_id: L'ID du document Grist
        table_id: L'ID de la table
        sort: Colonne de tri (optionnel, format: "colonne" ou "colonne:asc/desc")
        limit: Nombre maximum d'enregistrements à retourner (optionnel)
        
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - records (List): Liste des enregistrements
            - record_count (int): Nombre total d'enregistrements retournés
    """
    logger.info(f"Tool called: list_records with doc_id: {doc_id}, table_id: {table_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré",
                "records": [],
                "record_count": 0
            }
        
        records = await client.list_records(doc_id, table_id, sort=sort, limit=limit)
        
        limit_info = f" (limited to {limit})" if limit else ""
        sort_info = f" sorted by {sort}" if sort else ""
        
        return {
            "success": True,
            "message": f"Found {len(records)} records in table {table_id}{sort_info}{limit_info}",
            "records": [record.model_dump() for record in records],
            "record_count": len(records)
        }
    except Exception as e:
        logger.error(f"Error listing records: {e}")
        return {
            "success": False,
            "message": f"Error listing records for table {table_id} in document {doc_id}: {str(e)}",
            "records": [],
            "record_count": 0
        }


async def get_table_schema(doc_id: str, table_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Obtient le schéma détaillé d'une table Grist.
    
    Prérequis:
        - list_tables: Pour obtenir un table_id valide
        
    Flux de travail typique:
        1. list_tables(doc_id) → obtenir table_id
        2. get_table_schema(doc_id, table_id) → obtenir la structure détaillée
    
    Voir aussi:
        - list_columns: Pour une liste plus simple des colonnes
    
    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table
        
    Returns:
        Dict avec:
            - success (bool): Indique si l'opération a réussi
            - message (str): Message de succès ou d'erreur
            - schema (Dict): Schéma détaillé de la table au format frictionless
    """
    logger.info(f"Tool called: get_table_schema with doc_id: {doc_id}, table_id: {table_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        schema = await client.download_table_schema(doc_id, table_id)
        
        return {
            "success": True,
            "message": f"Retrieved schema for table {table_id}",
            "schema": schema
        }
    except Exception as e:
        logger.error(f"Error getting table schema: {e}")
        return {
            "success": False,
            "message": f"Error getting schema for table {table_id} in document {doc_id}: {str(e)}"
        }
