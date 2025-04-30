"""
Module implémentant des outils supplémentaires pour le MCP Grist Server.
Ces outils complètent les fonctionnalités existantes en ajoutant des capacités manquantes
de l'API Grist officielle.
"""

import json
import logging
import base64
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger("grist_additional_tools")

# Fonction pour enregistrer les outils supplémentaires
def register_additional_tools(mcp, get_client_func):
    """
    Enregistre les outils supplémentaires auprès du MCP Server
    
    Args:
        mcp: Objet FastMCP principal
        get_client_func: Fonction pour récupérer un client Grist configuré
    """
    logger.info("Enregistrement des outils supplémentaires pour l'API Grist")
    
    # === OUTILS DE GESTION DES DOCUMENTS ===
    
    @mcp.tool()
    async def create_document(
        workspace_id: int,
        doc_name: str,
        is_pinned: bool = False,
        ctx = None
    ) -> Dict[str, Any]:
        """
        Crée un nouveau document Grist vide dans un espace de travail.
        
        Args:
            workspace_id: ID de l'espace de travail où créer le document
            doc_name: Nom du nouveau document
            is_pinned: Si le document doit être épinglé
            ctx: Contexte MCP
            
        Returns:
            Informations sur le document créé, avec son ID
        """
        logger.info(f"Création d'un nouveau document: {doc_name} dans workspace {workspace_id}")
        
        try:
            client = get_client_func(ctx)
            
            doc_params = {
                "name": doc_name,
                "isPinned": is_pinned
            }
            
            result = await client._request(
                "POST",
                f"/workspaces/{workspace_id}/docs",
                json_data=doc_params
            )
            
            return {
                "success": True,
                "message": f"Document '{doc_name}' créé avec succès",
                "doc_id": result,
                "workspace_id": workspace_id,
                "doc_name": doc_name
            }
        except Exception as e:
            logger.error(f"Erreur lors de la création du document: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la création du document: {str(e)}",
                "workspace_id": workspace_id,
                "doc_name": doc_name
            }
    
    @mcp.tool()
    async def modify_document(
        doc_id: str,
        new_name: Optional[str] = None,
        is_pinned: Optional[bool] = None,
        ctx = None
    ) -> Dict[str, Any]:
        """
        Modifie les métadonnées d'un document Grist existant.
        
        Args:
            doc_id: ID du document à modifier
            new_name: Nouveau nom pour le document (optionnel)
            is_pinned: Nouvel état d'épinglage (optionnel)
            ctx: Contexte MCP
            
        Returns:
            Informations sur la modification
        """
        logger.info(f"Modification du document {doc_id}")
        
        try:
            client = get_client_func(ctx)
            
            # Construction des paramètres de modification
            doc_params = {}
            if new_name is not None:
                doc_params["name"] = new_name
            if is_pinned is not None:
                doc_params["isPinned"] = is_pinned
            
            if not doc_params:
                return {
                    "success": False,
                    "message": "Aucun paramètre de modification fourni",
                    "doc_id": doc_id
                }
            
            await client._request(
                "PATCH",
                f"/docs/{doc_id}",
                json_data=doc_params
            )
            
            modifications = []
            if new_name is not None:
                modifications.append(f"nom → '{new_name}'")
            if is_pinned is not None:
                modifications.append(f"épinglage → {'activé' if is_pinned else 'désactivé'}")
            
            return {
                "success": True,
                "message": f"Document modifié avec succès: {', '.join(modifications)}",
                "doc_id": doc_id,
                "modifications": doc_params
            }
        except Exception as e:
            logger.error(f"Erreur lors de la modification du document: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la modification du document: {str(e)}",
                "doc_id": doc_id
            }
    
    @mcp.tool()
    async def move_document(
        doc_id: str,
        target_workspace_id: int,
        ctx = None
    ) -> Dict[str, Any]:
        """
        Déplace un document Grist vers un autre espace de travail.
        
        Args:
            doc_id: ID du document à déplacer
            target_workspace_id: ID de l'espace de travail de destination
            ctx: Contexte MCP
            
        Returns:
            Informations sur le déplacement
        """
        logger.info(f"Déplacement du document {doc_id} vers l'espace de travail {target_workspace_id}")
        
        try:
            client = get_client_func(ctx)
            
            move_params = {
                "workspace": target_workspace_id
            }
            
            await client._request(
                "PATCH",
                f"/docs/{doc_id}/move",
                json_data=move_params
            )
            
            return {
                "success": True,
                "message": f"Document déplacé avec succès vers l'espace de travail {target_workspace_id}",
                "doc_id": doc_id,
                "target_workspace_id": target_workspace_id
            }
        except Exception as e:
            logger.error(f"Erreur lors du déplacement du document: {e}")
            return {
                "success": False,
                "message": f"Erreur lors du déplacement du document: {str(e)}",
                "doc_id": doc_id,
                "target_workspace_id": target_workspace_id
            }
    
    @mcp.tool()
    async def delete_document(
        doc_id: str,
        ctx = None
    ) -> Dict[str, Any]:
        """
        Supprime un document Grist.
        
        Args:
            doc_id: ID du document à supprimer
            ctx: Contexte MCP
            
        Returns:
            Informations sur la suppression
        """
        logger.info(f"Suppression du document {doc_id}")
        
        try:
            client = get_client_func(ctx)
            
            # Récupérer les informations du document avant sa suppression
            doc_info = await client._request(
                "GET",
                f"/docs/{doc_id}"
            )
            
            await client._request(
                "DELETE",
                f"/docs/{doc_id}"
            )
            
            return {
                "success": True,
                "message": f"Document supprimé avec succès",
                "doc_id": doc_id,
                "doc_name": doc_info.get("name", "Document inconnu")
            }
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du document: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la suppression du document: {str(e)}",
                "doc_id": doc_id
            }
    
    # === OUTILS DE GESTION DES TABLES ===
    
    @mcp.tool()
    async def create_table(
        doc_id: str,
        table_name: str,
        columns: List[Dict[str, Any]],
        ctx = None
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle table dans un document Grist avec les colonnes spécifiées.
        
        Args:
            doc_id: ID du document
            table_name: Nom de la table à créer
            columns: Liste des colonnes à créer (chaque colonne est un dict avec 'id' et 'fields')
            ctx: Contexte MCP
            
        Returns:
            Informations sur la table créée
            
        Exemple de paramètre columns:
        [
            {"id": "nom", "fields": {"label": "Nom", "type": "Text"}},
            {"id": "age", "fields": {"label": "Âge", "type": "Int"}}
        ]
        """
        logger.info(f"Création de la table {table_name} dans le document {doc_id}")
        
        try:
            client = get_client_func(ctx)
            
            # Préparation des données pour la création de la table
            create_params = {
                "tables": [
                    {
                        "id": table_name,
                        "columns": columns
                    }
                ]
            }
            
            result = await client._request(
                "POST",
                f"/docs/{doc_id}/tables",
                json_data=create_params
            )
            
            return {
                "success": True,
                "message": f"Table '{table_name}' créée avec succès",
                "doc_id": doc_id,
                "table_id": table_name,
                "columns_created": len(columns),
                "table_info": result
            }
        except Exception as e:
            logger.error(f"Erreur lors de la création de la table: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la création de la table: {str(e)}",
                "doc_id": doc_id,
                "table_name": table_name
            }
    
    @mcp.tool()
    async def modify_table(
        doc_id: str,
        table_id: str,
        new_fields: Dict[str, Any],
        ctx = None
    ) -> Dict[str, Any]:
        """
        Modifie les propriétés d'une table existante dans un document Grist.
        
        Args:
            doc_id: ID du document
            table_id: ID de la table à modifier
            new_fields: Nouvelles propriétés pour la table
            ctx: Contexte MCP
            
        Returns:
            Informations sur la modification
        """
        logger.info(f"Modification de la table {table_id} dans le document {doc_id}")
        
        try:
            client = get_client_func(ctx)
            
            # Préparation des données pour la modification de la table
            modify_params = {
                "tables": [
                    {
                        "id": table_id,
                        "fields": new_fields
                    }
                ]
            }
            
            await client._request(
                "PATCH",
                f"/docs/{doc_id}/tables",
                json_data=modify_params
            )
            
            return {
                "success": True,
                "message": f"Table '{table_id}' modifiée avec succès",
                "doc_id": doc_id,
                "table_id": table_id,
                "modifications": new_fields
            }
        except Exception as e:
            logger.error(f"Erreur lors de la modification de la table: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la modification de la table: {str(e)}",
                "doc_id": doc_id,
                "table_id": table_id
            }
    
    # === OUTILS DE GESTION DES COLONNES ===
    
    @mcp.tool()
    async def add_columns(
        doc_id: str,
        table_id: str,
        columns: List[Dict[str, Any]],
        ctx = None
    ) -> Dict[str, Any]:
        """
        Ajoute de nouvelles colonnes à une table existante.
        
        Args:
            doc_id: ID du document
            table_id: ID de la table
            columns: Liste des colonnes à ajouter (chaque colonne est un dict avec 'id' et 'fields')
            ctx: Contexte MCP
            
        Returns:
            Informations sur les colonnes ajoutées
            
        Exemple de paramètre columns:
        [
            {"id": "description", "fields": {"label": "Description", "type": "Text"}},
            {"id": "priorite", "fields": {"label": "Priorité", "type": "Choice", "widgetOptions": "{\"choices\":[\"Basse\",\"Moyenne\",\"Haute\"]}"}}   
        ]
        """
        logger.info(f"Ajout de {len(columns)} colonnes à la table {table_id} dans le document {doc_id}")
        
        try:
            client = get_client_func(ctx)
            
            # Préparation des données pour l'ajout des colonnes
            create_params = {
                "columns": columns
            }
            
            result = await client._request(
                "POST",
                f"/docs/{doc_id}/tables/{table_id}/columns",
                json_data=create_params
            )
            
            return {
                "success": True,
                "message": f"{len(columns)} colonnes ajoutées avec succès à la table '{table_id}'",
                "doc_id": doc_id,
                "table_id": table_id,
                "columns_added": [col["id"] for col in columns],
                "column_info": result
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des colonnes: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de l'ajout des colonnes: {str(e)}",
                "doc_id": doc_id,
                "table_id": table_id
            }
    
    @mcp.tool()
    async def modify_columns(
        doc_id: str,
        table_id: str,
        columns: List[Dict[str, Any]],
        ctx = None
    ) -> Dict[str, Any]:
        """
        Modifie des colonnes existantes dans une table.
        
        Args:
            doc_id: ID du document
            table_id: ID de la table
            columns: Liste des colonnes à modifier (chaque colonne est un dict avec 'id' et 'fields')
            ctx: Contexte MCP
            
        Returns:
            Informations sur les colonnes modifiées
            
        Exemple de paramètre columns:
        [
            {"id": "nom", "fields": {"label": "Nom complet"}},
            {"id": "age", "fields": {"label": "Âge (années)"}}
        ]
        """
        logger.info(f"Modification de {len(columns)} colonnes dans la table {table_id} du document {doc_id}")
        
        try:
            client = get_client_func(ctx)
            
            # Préparation des données pour la modification des colonnes
            modify_params = {
                "columns": columns
            }
            
            await client._request(
                "PATCH",
                f"/docs/{doc_id}/tables/{table_id}/columns",
                json_data=modify_params
            )
            
            return {
                "success": True,
                "message": f"{len(columns)} colonnes modifiées avec succès dans la table '{table_id}'",
                "doc_id": doc_id,
                "table_id": table_id,
                "columns_modified": [col["id"] for col in columns]
            }
        except Exception as e:
            logger.error(f"Erreur lors de la modification des colonnes: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la modification des colonnes: {str(e)}",
                "doc_id": doc_id,
                "table_id": table_id
            }
    
    @mcp.tool()
    async def delete_column(
        doc_id: str,
        table_id: str,
        column_id: str,
        ctx = None
    ) -> Dict[str, Any]:
        """
        Supprime une colonne d'une table.
        
        Args:
            doc_id: ID du document
            table_id: ID de la table
            column_id: ID de la colonne à supprimer
            ctx: Contexte MCP
            
        Returns:
            Informations sur la suppression
        """
        logger.info(f"Suppression de la colonne {column_id} de la table {table_id} dans le document {doc_id}")
        
        try:
            client = get_client_func(ctx)
            
            await client._request(
                "DELETE",
                f"/docs/{doc_id}/tables/{table_id}/columns/{column_id}"
            )
            
            return {
                "success": True,
                "message": f"Colonne '{column_id}' supprimée avec succès de la table '{table_id}'",
                "doc_id": doc_id,
                "table_id": table_id,
                "column_id": column_id
            }
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la colonne: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la suppression de la colonne: {str(e)}",
                "doc_id": doc_id,
                "table_id": table_id,
                "column_id": column_id
            }
    
    # === OUTILS SQL ===
    
    @mcp.tool()
    async def execute_sql_query(
        doc_id: str,
        sql_query: str,
        parameters: Optional[List[Any]] = None,
        timeout_ms: Optional[int] = 1000,
        ctx = None
    ) -> Dict[str, Any]:
        """
        Exécute une requête SQL sur un document Grist.
        
        Args:
            doc_id: ID du document
            sql_query: Requête SQL à exécuter (SELECT uniquement)
            parameters: Paramètres pour la requête SQL (optionnel)
            timeout_ms: Délai d'expiration en millisecondes (1000 par défaut)
            ctx: Contexte MCP
            
        Returns:
            Résultats de la requête SQL
            
        Notes:
            - Seules les requêtes SELECT sont autorisées
            - Pas de point-virgule à la fin de la requête
            - Les clauses WITH sont autorisées
        """
        logger.info(f"Exécution d'une requête SQL sur le document {doc_id}")
        
        try:
            client = get_client_func(ctx)
            
            # Nettoyage basique de la requête SQL
            sql_query = sql_query.strip()
            if sql_query.endswith(";"):
                sql_query = sql_query[:-1]
            
            # Vérification de sécurité basique
            if not sql_query.lower().startswith(("select", "with")):
                return {
                    "success": False,
                    "message": "Seules les requêtes SELECT (avec clause WITH optionnelle) sont autorisées",
                    "doc_id": doc_id
                }
            
            # Préparation des données pour la requête SQL
            query_params = {
                "sql": sql_query
            }
            
            if parameters:
                query_params["args"] = parameters
            
            if timeout_ms:
                query_params["timeout"] = timeout_ms
            
            result = await client._request(
                "POST",
                f"/docs/{doc_id}/sql",
                json_data=query_params
            )
            
            return {
                "success": True,
                "message": f"Requête SQL exécutée avec succès",
                "doc_id": doc_id,
                "query": sql_query,
                "record_count": len(result.get("records", [])),
                "records": result.get("records", [])
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête SQL: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de l'exécution de la requête SQL: {str(e)}",
                "doc_id": doc_id,
                "query": sql_query
            }
    
    # === OUTILS DE TÉLÉCHARGEMENT ET EXPORT ===
    
    @mcp.tool()
    async def download_table_as_csv(
        doc_id: str,
        table_id: str,
        header_format: str = "label",
        ctx = None
    ) -> Dict[str, Any]:
        """
        Génère l'URL pour télécharger une table au format CSV.
        
        Args:
            doc_id: ID du document
            table_id: ID de la table
            header_format: Format des en-têtes ('label' ou 'colId')
            ctx: Contexte MCP
            
        Returns:
            URL pour télécharger le CSV et informations associées
        """
        logger.info(f"Génération d'URL pour télécharger la table {table_id} au format CSV")
        
        try:
            client = get_client_func(ctx)
            
            # Construction de l'URL
            base_url = client.api_url.rstrip('/')
            csv_url = f"{base_url}/docs/{doc_id}/download/csv?tableId={table_id}&header={header_format}"
            
            return {
                "success": True,
                "message": f"URL de téléchargement CSV générée avec succès",
                "doc_id": doc_id,
                "table_id": table_id,
                "download_url": csv_url,
                "header_format": header_format,
                "usage": "Utilisez cette URL avec votre clé API dans un header 'Authorization: Bearer VOTRE_CLE_API'"
            }
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'URL CSV: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la génération de l'URL CSV: {str(e)}",
                "doc_id": doc_id,
                "table_id": table_id
            }
    
    @mcp.tool()
    async def download_document_as_xlsx(
        doc_id: str,
        header_format: str = "label",
        ctx = None
    ) -> Dict[str, Any]:
        """
        Génère l'URL pour télécharger un document au format Excel (XLSX).
        
        Args:
            doc_id: ID du document
            header_format: Format des en-têtes ('label' ou 'colId')
            ctx: Contexte MCP
            
        Returns:
            URL pour télécharger le fichier Excel et informations associées
        """
        logger.info(f"Génération d'URL pour télécharger le document {doc_id} au format Excel")
        
        try:
            client = get_client_func(ctx)
            
            # Construction de l'URL
            base_url = client.api_url.rstrip('/')
            xlsx_url = f"{base_url}/docs/{doc_id}/download/xlsx?header={header_format}"
            
            return {
                "success": True,
                "message": f"URL de téléchargement Excel générée avec succès",
                "doc_id": doc_id,
                "download_url": xlsx_url,
                "header_format": header_format,
                "usage": "Utilisez cette URL avec votre clé API dans un header 'Authorization: Bearer VOTRE_CLE_API'"
            }
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'URL Excel: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la génération de l'URL Excel: {str(e)}",
                "doc_id": doc_id
            }
    
    @mcp.tool()
    async def get_table_schema(
        doc_id: str,
        table_id: str,
        header_format: str = "label",
        ctx = None
    ) -> Dict[str, Any]:
        """
        Récupère le schéma d'une table Grist au format table-schema.
        
        Args:
            doc_id: ID du document
            table_id: ID de la table
            header_format: Format des en-têtes ('label' ou 'colId')
            ctx: Contexte MCP
            
        Returns:
            Schéma de la table au format table-schema
        """
        logger.info(f"Récupération du schéma de la table {table_id}")
        
        try:
            client = get_client_func(ctx)
            
            result = await client._request(
                "GET",
                f"/docs/{doc_id}/download/table-schema?tableId={table_id}&header={header_format}"
            )
            
            return {
                "success": True,
                "message": f"Schéma de la table récupéré avec succès",
                "doc_id": doc_id,
                "table_id": table_id,
                "schema": result
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du schéma de la table: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de la récupération du schéma de la table: {str(e)}",
                "doc_id": doc_id,
                "table_id": table_id
            }
            
    outils = {
        "create_document": create_document,
        "modify_document": modify_document,
        "move_document": move_document,
        "delete_document": delete_document,
        "create_table": create_table,
        "modify_table": modify_table,
        "add_columns": add_columns,
        "modify_columns": modify_columns,
        "delete_column": delete_column,
        "execute_sql_query": execute_sql_query,
        "download_table_as_csv": download_table_as_csv,
        "download_document_as_xlsx": download_document_as_xlsx,
        "get_table_schema": get_table_schema
    }
    
    return outils