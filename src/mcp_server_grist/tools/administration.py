"""
Outils d'administration pour l'API Grist.

Ce module contient des outils MCP pour gérer les aspects administratifs
de Grist: création et modification d'objets, gestion des accès.

Corrections v0.2.0:
- create_table: format payload corrigé (id au lieu de tableId, columns avec fields)
- modify_table: format payload corrigé
- create_column: gestion widgetOptions comme JSON string + nouveaux paramètres
- modify_column: gestion widgetOptions comme JSON string + nouveaux paramètres
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context

from ..client import get_client

# Configurer le logger
logger = logging.getLogger("grist_mcp_server")


def register_admin_tools(mcp_server):
    """
    Enregistre tous les outils d'administration sur le serveur MCP.
    
    Args:
        mcp_server: L'instance du serveur MCP sur laquelle enregistrer les outils.
    """
    # Organisation
    mcp_server.tool()(modify_organization)
    mcp_server.tool()(delete_organization)
    
    # Workspace
    mcp_server.tool()(create_workspace)
    mcp_server.tool()(modify_workspace)
    mcp_server.tool()(delete_workspace)
    
    # Document
    mcp_server.tool()(create_document)
    mcp_server.tool()(modify_document)
    mcp_server.tool()(delete_document)
    mcp_server.tool()(move_document)
    mcp_server.tool()(force_reload_document)
    mcp_server.tool()(delete_document_history)
    
    # Table
    mcp_server.tool()(create_table)
    mcp_server.tool()(modify_table)
    
    # Column
    mcp_server.tool()(create_column)
    mcp_server.tool()(modify_column)
    mcp_server.tool()(delete_column)


# --- Organisation Management ---

async def modify_organization(
    org_id: Union[int, str],
    name: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modifie les propriétés d'une organisation.
    
    Prérequis:
        - list_organizations: Pour obtenir un org_id valide
    
    Args:
        org_id: L'ID de l'organisation à modifier
        name: Nouveau nom pour l'organisation (optionnel)
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: modify_organization with org_id: {org_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        org_data = {}
        if name is not None:
            org_data["name"] = name
        
        if not org_data:
            return {
                "success": False,
                "message": "Aucune donnée de modification fournie"
            }
        
        await client.modify_org(org_id, org_data)
        
        return {
            "success": True,
            "message": f"Organisation {org_id} modifiée avec succès"
        }
    except Exception as e:
        logger.error(f"Error modifying organization: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la modification de l'organisation: {str(e)}"
        }


async def delete_organization(
    org_id: Union[int, str],
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Supprime une organisation.
    
    Attention:
        Cette action est irréversible et supprimera tous les espaces de travail,
        documents et données associés à cette organisation.
    
    Args:
        org_id: L'ID de l'organisation à supprimer
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: delete_organization with org_id: {org_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        await client.delete_org(org_id)
        
        return {
            "success": True,
            "message": f"Organisation {org_id} supprimée avec succès"
        }
    except Exception as e:
        logger.error(f"Error deleting organization: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la suppression de l'organisation: {str(e)}"
        }


# --- Workspace Management ---

async def create_workspace(
    org_id: Union[int, str],
    name: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Crée un nouvel espace de travail dans une organisation.
    
    Prérequis:
        - list_organizations: Pour obtenir un org_id valide
    
    Flux de travail typique:
        1. list_organizations() → obtenir org_id
        2. create_workspace(org_id, "Nom") → créer l'espace de travail
        3. list_workspaces(org_id) → vérifier la création
    
    Args:
        org_id: L'ID de l'organisation
        name: Nom du nouvel espace de travail
        
    Returns:
        Dict avec statut, message et ID de l'espace de travail créé
    """
    logger.info(f"Tool called: create_workspace with org_id: {org_id}, name: {name}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        workspace_data = {"name": name}
        workspace_id = await client.create_workspace(org_id, workspace_data)
        
        return {
            "success": True,
            "message": f"Espace de travail '{name}' créé avec succès",
            "workspace_id": workspace_id
        }
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la création de l'espace de travail: {str(e)}"
        }


async def modify_workspace(
    workspace_id: int,
    name: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modifie les propriétés d'un espace de travail.
    
    Prérequis:
        - list_workspaces: Pour obtenir un workspace_id valide
    
    Args:
        workspace_id: L'ID de l'espace de travail à modifier
        name: Nouveau nom pour l'espace de travail (optionnel)
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: modify_workspace with workspace_id: {workspace_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        workspace_data = {}
        if name is not None:
            workspace_data["name"] = name
        
        if not workspace_data:
            return {
                "success": False,
                "message": "Aucune donnée de modification fournie"
            }
        
        await client.modify_workspace(workspace_id, workspace_data)
        
        return {
            "success": True,
            "message": f"Espace de travail {workspace_id} modifié avec succès"
        }
    except Exception as e:
        logger.error(f"Error modifying workspace: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la modification de l'espace de travail: {str(e)}"
        }


async def delete_workspace(
    workspace_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Supprime un espace de travail.
    
    Attention:
        Cette action est irréversible et supprimera tous les documents
        et données associés à cet espace de travail.
    
    Args:
        workspace_id: L'ID de l'espace de travail à supprimer
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: delete_workspace with workspace_id: {workspace_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        await client.delete_workspace(workspace_id)
        
        return {
            "success": True,
            "message": f"Espace de travail {workspace_id} supprimé avec succès"
        }
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la suppression de l'espace de travail: {str(e)}"
        }


# --- Document Management ---

async def create_document(
    workspace_id: int,
    name: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Crée un nouveau document dans un espace de travail.
    
    Prérequis:
        - list_workspaces: Pour obtenir un workspace_id valide
    
    Flux de travail typique:
        1. list_workspaces(org_id) → obtenir workspace_id
        2. create_document(workspace_id, "Nom") → créer le document
        3. list_documents(workspace_id) → vérifier la création
    
    Args:
        workspace_id: L'ID de l'espace de travail
        name: Nom du nouveau document
        
    Returns:
        Dict avec statut, message et ID du document créé
    """
    logger.info(f"Tool called: create_document with workspace_id: {workspace_id}, name: {name}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        doc_data = {"name": name}
        doc_id = await client.create_doc(workspace_id, doc_data)
        
        return {
            "success": True,
            "message": f"Document '{name}' créé avec succès",
            "doc_id": doc_id
        }
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la création du document: {str(e)}"
        }


async def modify_document(
    doc_id: str,
    name: Optional[str] = None,
    is_pinned: Optional[bool] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modifie les propriétés d'un document.
    
    Prérequis:
        - list_documents: Pour obtenir un doc_id valide
    
    Args:
        doc_id: L'ID du document à modifier
        name: Nouveau nom pour le document (optionnel)
        is_pinned: État d'épinglage du document (optionnel)
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: modify_document with doc_id: {doc_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        doc_data = {}
        if name is not None:
            doc_data["name"] = name
        if is_pinned is not None:
            doc_data["isPinned"] = is_pinned
        
        if not doc_data:
            return {
                "success": False,
                "message": "Aucune donnée de modification fournie"
            }
        
        await client.modify_doc(doc_id, doc_data)
        
        return {
            "success": True,
            "message": f"Document {doc_id} modifié avec succès"
        }
    except Exception as e:
        logger.error(f"Error modifying document: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la modification du document: {str(e)}"
        }


async def delete_document(
    doc_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Supprime un document.
    
    Attention:
        Cette action est irréversible et supprimera toutes les données
        associées à ce document.
    
    Args:
        doc_id: L'ID du document à supprimer
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: delete_document with doc_id: {doc_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        await client.delete_doc(doc_id)
        
        return {
            "success": True,
            "message": f"Document {doc_id} supprimé avec succès"
        }
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la suppression du document: {str(e)}"
        }


async def move_document(
    doc_id: str,
    target_workspace_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Déplace un document vers un autre espace de travail.
    
    Prérequis:
        - list_documents: Pour obtenir un doc_id valide
        - list_workspaces: Pour obtenir un workspace_id valide
    
    Args:
        doc_id: L'ID du document à déplacer
        target_workspace_id: L'ID de l'espace de travail de destination
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: move_document with doc_id: {doc_id}, target_workspace_id: {target_workspace_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        await client.move_doc(doc_id, target_workspace_id)
        
        return {
            "success": True,
            "message": f"Document {doc_id} déplacé vers l'espace de travail {target_workspace_id} avec succès"
        }
    except Exception as e:
        logger.error(f"Error moving document: {e}")
        return {
            "success": False,
            "message": f"Erreur lors du déplacement du document: {str(e)}"
        }


async def force_reload_document(
    doc_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Force le rechargement d'un document.
    
    Utile en cas d'incohérences ou de problèmes de synchronisation.
    
    Args:
        doc_id: L'ID du document à recharger
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: force_reload_document with doc_id: {doc_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        await client.force_reload_doc(doc_id)
        
        return {
            "success": True,
            "message": f"Document {doc_id} rechargé avec succès"
        }
    except Exception as e:
        logger.error(f"Error reloading document: {e}")
        return {
            "success": False,
            "message": f"Erreur lors du rechargement du document: {str(e)}"
        }


async def delete_document_history(
    doc_id: str,
    keep: int = 1000,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Supprime l'historique d'un document, ne conservant que les dernières actions.
    
    Utile pour réduire la taille des documents volumineux.
    
    Args:
        doc_id: L'ID du document
        keep: Nombre d'actions récentes à conserver (défaut: 1000)
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: delete_document_history with doc_id: {doc_id}, keep: {keep}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        await client.delete_doc_history(doc_id, keep)
        
        return {
            "success": True,
            "message": f"Historique du document {doc_id} supprimé avec succès, conservant {keep} actions récentes"
        }
    except Exception as e:
        logger.error(f"Error deleting document history: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la suppression de l'historique du document: {str(e)}"
        }


# --- Table Management ---

async def create_table(
    doc_id: str,
    table_id: str,
    columns: Optional[List[Dict[str, Any]]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Crée une nouvelle table dans un document.

    Prérequis:
        - list_documents: Pour obtenir un doc_id valide

    Flux de travail typique:
        1. list_documents(workspace_id) → obtenir doc_id
        2. create_table(doc_id, "TableName", columns=[...]) → créer la table
        3. list_tables(doc_id) → vérifier la création

    Args:
        doc_id: L'ID du document
        table_id: ID de la nouvelle table (doit être unique dans le document)
        columns: Liste des définitions de colonnes (optionnel)
                Exemple: [
                    {"id": "name", "type": "Text", "label": "Nom"},
                    {"id": "status", "type": "Choice", "widgetOptions": {"choices": ["A", "B", "C"]}},
                    {"id": "amount", "type": "Numeric"}
                ]

    Returns:
        Dict avec statut, message et détails de la table créée
    """
    logger.info(f"Tool called: create_table with doc_id: {doc_id}, table_id: {table_id}")

    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }

        # CORRECTION v0.2.0: Format API Grist corrigé
        # Structure attendue: {"tables": [{"id": "X", "columns": [{"id": "col", "fields": {...}}]}]}
        prepared_columns = []
        for col in (columns or []):
            col_id = col.get("id")
            if not col_id:
                continue

            # Séparer l'ID des fields
            fields = {}
            for key, value in col.items():
                if key == "id":
                    continue
                # widgetOptions doit être une string JSON
                if key == "widgetOptions":
                    if isinstance(value, dict):
                        fields[key] = json.dumps(value)
                    elif isinstance(value, str):
                        fields[key] = value
                else:
                    fields[key] = value

            prepared_columns.append({
                "id": col_id,
                "fields": fields
            })

        table_data = {
            "tables": [
                {
                    "id": table_id,  # CORRECTION: "id" au lieu de "tableId"
                    "columns": prepared_columns
                }
            ]
        }

        result = await client.create_tables(doc_id, table_data)

        # Vérifier si l'ID réel correspond à celui demandé
        response = {
            "success": True,
            "message": f"Table '{table_id}' créée avec succès",
            "table": result[0] if result else {"id": table_id}
        }

        if result and result[0].get("id") != table_id:
            actual_id = result[0].get("id")
            response["warning"] = f"L'ID demandé '{table_id}' a été modifié en '{actual_id}' par Grist"

        return response
    except Exception as e:
        logger.error(f"Error creating table: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la création de la table: {str(e)}"
        }


async def modify_table(
    doc_id: str,
    table_id: str,
    new_table_id: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modifie les propriétés d'une table.

    Prérequis:
        - list_tables: Pour obtenir un table_id valide

    Args:
        doc_id: L'ID du document
        table_id: L'ID actuel de la table
        new_table_id: Nouvel ID pour la table (optionnel)

    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: modify_table with doc_id: {doc_id}, table_id: {table_id}")

    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }

        if not new_table_id:
            return {
                "success": False,
                "message": "Aucune modification demandée (new_table_id requis)"
            }

        # CORRECTION v0.2.0: Format API Grist corrigé
        # Structure attendue: {"tables": [{"id": "currentId", "fields": {"tableId": "newId"}}]}
        table_data = {
            "tables": [
                {
                    "id": table_id,  # CORRECTION: "id" au lieu de "tableId"
                    "fields": {
                        "tableId": new_table_id  # Le nouveau nom va dans fields.tableId
                    }
                }
            ]
        }

        await client.modify_tables(doc_id, table_data)

        return {
            "success": True,
            "message": f"Table '{table_id}' renommée en '{new_table_id}' avec succès"
        }
    except Exception as e:
        logger.error(f"Error modifying table: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la modification de la table: {str(e)}"
        }


# --- Column Management ---

async def create_column(
    doc_id: str,
    table_id: str,
    column_id: str,
    column_type: str = "Text",
    label: Optional[str] = None,
    formula: Optional[str] = None,
    widget_options: Optional[Dict[str, Any]] = None,
    visible_col: Optional[int] = None,
    untie_col_id_from_label: bool = True,
    description: Optional[str] = None,
    choices: Optional[List[str]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Crée une nouvelle colonne dans une table.

    Prérequis:
        - list_tables: Pour obtenir un table_id valide

    Flux de travail typique:
        1. list_tables(doc_id) → obtenir table_id
        2. create_column(doc_id, table_id, "col_name", "Text", "Nom") → créer la colonne
        3. list_columns(doc_id, table_id) → vérifier la création

    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table
        column_id: ID de la nouvelle colonne (doit être unique dans la table)
        column_type: Type de données. Types supportés:
            - Text, Numeric, Int, Bool, Date, DateTime
            - Choice, ChoiceList (avec paramètre choices)
            - Ref:TableId, RefList:TableId (références)
            - Attachments
        label: Libellé d'affichage de la colonne (optionnel)
        formula: Formule Python pour colonnes calculées (optionnel)
        widget_options: Options d'affichage comme dict (optionnel)
        visible_col: colRef de la colonne à afficher pour les Ref (optionnel)
        untie_col_id_from_label: Dissocier l'ID du label (défaut: True)
        description: Description de la colonne (optionnel)
        choices: Liste de choix pour Choice/ChoiceList (optionnel)

    Returns:
        Dict avec statut, message et détails de la colonne créée

    Examples:
        # Colonne texte simple
        create_column(doc_id, "Table1", "name", "Text", label="Nom")

        # Colonne choix
        create_column(doc_id, "Table1", "status", "Choice",
                      choices=["Actif", "Inactif", "En attente"])

        # Colonne référence
        create_column(doc_id, "Table1", "owner", "Ref:Users",
                      label="Propriétaire", visible_col=5)

        # Colonne calculée
        create_column(doc_id, "Table1", "full_name", "Text",
                      formula="$first_name + ' ' + $last_name")
    """
    logger.info(f"Tool called: create_column with doc_id: {doc_id}, table_id: {table_id}, column_id: {column_id}")

    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }

        # CORRECTION v0.2.0: Format amélioré avec nouveaux paramètres
        fields = {
            "type": column_type,
            "untieColIdFromLabel": untie_col_id_from_label
        }

        if label:
            fields["label"] = label
        if formula:
            fields["formula"] = formula
            fields["isFormula"] = True
        if description:
            fields["description"] = description
        if visible_col is not None:
            fields["visibleCol"] = visible_col

        # CORRECTION v0.2.0: widgetOptions doit être une string JSON
        opts = widget_options.copy() if widget_options else {}
        if choices and column_type in ("Choice", "ChoiceList"):
            opts["choices"] = choices
        if opts:
            fields["widgetOptions"] = json.dumps(opts)

        column_data = {
            "columns": [
                {
                    "id": column_id,
                    "fields": fields
                }
            ]
        }

        result = await client.create_columns(doc_id, table_id, column_data)

        return {
            "success": True,
            "message": f"Colonne '{column_id}' créée avec succès",
            "column": result[0] if result else {"id": column_id}
        }
    except Exception as e:
        logger.error(f"Error creating column: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la création de la colonne: {str(e)}"
        }


async def modify_column(
    doc_id: str,
    table_id: str,
    column_id: str,
    new_column_id: Optional[str] = None,
    column_type: Optional[str] = None,
    label: Optional[str] = None,
    formula: Optional[str] = None,
    widget_options: Optional[Dict[str, Any]] = None,
    visible_col: Optional[int] = None,
    untie_col_id_from_label: Optional[bool] = None,
    description: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modifie les propriétés d'une colonne.

    Prérequis:
        - list_columns: Pour obtenir un column_id valide

    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table
        column_id: L'ID actuel de la colonne
        new_column_id: Nouvel ID pour la colonne (optionnel)
        column_type: Nouveau type de données (optionnel)
        label: Nouveau libellé d'affichage (optionnel)
        formula: Nouvelle formule (optionnel, "" pour supprimer)
        widget_options: Nouvelles options d'affichage (optionnel)
        visible_col: Nouveau colRef pour les Ref (optionnel)
        untie_col_id_from_label: Dissocier l'ID du label (optionnel)
        description: Nouvelle description (optionnel)

    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: modify_column with doc_id: {doc_id}, table_id: {table_id}, column_id: {column_id}")

    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }

        fields = {}

        # Ajouter les champs à modifier s'ils sont fournis
        if new_column_id:
            fields["colId"] = new_column_id
        if column_type:
            fields["type"] = column_type
        if label is not None:
            fields["label"] = label
        if formula is not None:  # Permettre de vider la formule avec une chaîne vide
            fields["formula"] = formula
            fields["isFormula"] = bool(formula)
        if description is not None:
            fields["description"] = description
        if visible_col is not None:
            fields["visibleCol"] = visible_col
        if untie_col_id_from_label is not None:
            fields["untieColIdFromLabel"] = untie_col_id_from_label

        # CORRECTION v0.2.0: widgetOptions doit être une string JSON
        if widget_options is not None:
            fields["widgetOptions"] = json.dumps(widget_options)

        if not fields:
            return {
                "success": False,
                "message": "Aucune modification demandée"
            }

        column_data = {
            "columns": [
                {
                    "id": column_id,
                    "fields": fields
                }
            ]
        }

        await client.modify_columns(doc_id, table_id, column_data)

        message = f"Colonne '{column_id}' modifiée avec succès"
        if new_column_id:
            message += f" (renommée en '{new_column_id}')"

        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        logger.error(f"Error modifying column: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la modification de la colonne: {str(e)}"
        }


async def delete_column(
    doc_id: str,
    table_id: str,
    column_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Supprime une colonne d'une table.
    
    Attention:
        Cette action est irréversible et supprimera toutes les données
        associées à cette colonne.
    
    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table
        column_id: L'ID de la colonne à supprimer
        
    Returns:
        Dict avec statut et message de l'opération
    """
    logger.info(f"Tool called: delete_column with doc_id: {doc_id}, table_id: {table_id}, column_id: {column_id}")
    
    try:
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré"
            }
        
        await client.delete_column(doc_id, table_id, column_id)
        
        return {
            "success": True,
            "message": f"Colonne '{column_id}' supprimée avec succès"
        }
    except Exception as e:
        logger.error(f"Error deleting column: {e}")
        return {
            "success": False,
            "message": f"Erreur lors de la suppression de la colonne: {str(e)}"
        }
