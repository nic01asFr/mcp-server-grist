"""
Outils de requêtes SQL pour l'API Grist.

Ce module contient des outils MCP pour exécuter des requêtes SQL
sur les données Grist, permettant filtrage, tri et analyse.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context

from ..client import get_client

# Configurer le logger
logger = logging.getLogger("grist_mcp_server")


def register_query_tools(mcp_server):
    """
    Enregistre tous les outils de requêtes SQL sur le serveur MCP.
    
    Args:
        mcp_server: L'instance du serveur MCP sur laquelle enregistrer les outils.
    """
    # Enregistrement des outils sur le serveur MCP
    mcp_server.tool()(filter_sql_query)
    mcp_server.tool()(execute_sql_query)


async def filter_sql_query(
    doc_id: str,
    table_id: str,
    columns: Optional[List[str]] = None,
    where_conditions: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Exécute une requête SQL de filtrage sur une table Grist.
    
    Version simplifiée pour requêtes SQL courantes sans écrire de SQL.
    Pour requêtes complexes, utiliser execute_sql_query.
    
    Prérequis recommandés:
        - list_tables(doc_id) : Vérifier l'existence de la table
        - list_columns(doc_id, table_id) : Connaître les colonnes disponibles
    
    Alternative à:
        - list_records : Quand vous avez besoin de filtrer/trier
        - execute_sql_query : Version simplifiée pour cas courants
    
    Flux de travail typique:
        1. list_columns(doc_id, table_id) → identifier les colonnes
        2. filter_sql_query(doc_id, table_id, 
                          where_conditions={"status": "actif"},
                          order_by="date_creation DESC",
                          limit=10)
        3. Traiter les enregistrements retournés
    
    Cas d'usage:
        - Filtrage simple: where_conditions={"status": "actif"}
        - Filtrage multiple: where_conditions={"status": "actif", "type": "A"}
        - Tri: order_by="nom" ou order_by="valeur DESC"
        - Pagination: limit=20
        - Colonnes spécifiques: columns=["nom", "valeur", "date"]
    
    Args:
        doc_id: ID du document
        table_id: ID de la table à requêter
        columns: Liste des colonnes à retourner (None = toutes)
        where_conditions: Dict de conditions (AND implicite entre conditions)
        order_by: Colonne de tri avec direction optionnelle (ex: "nom DESC")
        limit: Nombre max de résultats
        
    Returns:
        Dict avec les enregistrements filtrés et métadonnées de requête
    """
    logger.info(f"Tool called: filter_sql_query for doc_id: {doc_id}, table_id: {table_id}")
    
    try:
        # Construire la requête SQL
        columns_str = "*"
        if columns:
            columns_str = ", ".join([f'"{col}"' for col in columns])
        
        sql_query = f'SELECT {columns_str} FROM "{table_id}"'
        
        params = []
        
        # Ajouter les conditions WHERE
        if where_conditions:
            conditions = []
            for col, value in where_conditions.items():
                conditions.append(f'"{col}" = ?')
                params.append(value)
            
            if conditions:
                sql_query += f" WHERE {' AND '.join(conditions)}"
        
        # Ajouter ORDER BY
        if order_by:
            sql_query += f" ORDER BY {order_by}"
        
        # Ajouter LIMIT
        if limit is not None:
            sql_query += f" LIMIT {limit}"
        
        # Exécuter la requête SQL générée via execute_sql_query
        return await execute_sql_query(
            doc_id=doc_id,
            sql_query=sql_query,
            parameters=params,
            ctx=ctx
        )
        
    except Exception as e:
        logger.error(f"Error in filter_sql_query: {str(e)}")
        return {
            "success": False,
            "message": f"Erreur lors du filtrage SQL: {str(e)}",
            "query": "",
            "records": [],
            "record_count": 0
        }


async def execute_sql_query(
    doc_id: str,
    sql_query: str,
    parameters: Optional[List[Any]] = None,
    timeout_ms: Optional[int] = 1000,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Exécute une requête SQL personnalisée sur un document Grist.
    
    Permet d'exécuter des requêtes SQL complexes avec jointures,
    agrégations et sous-requêtes.
    
    Prérequis:
        - list_tables: Pour connaître les noms des tables disponibles
        - list_columns: Pour connaître les noms des colonnes à requêter
    
    Flux de travail typique:
        1. list_tables(doc_id) → identifier les tables
        2. list_columns(doc_id, table_id) → identifier les colonnes
        3. execute_sql_query(doc_id, "SELECT t1.col1, t2.col2 FROM Table1 t1 
                                    JOIN Table2 t2 ON t1.id = t2.ref_id
                                    WHERE t1.status = ?", 
                          parameters=["active"])
    
    Sécurité:
        - Utilisez toujours des paramètres liés (?) pour les valeurs variables
        - Seules les requêtes SELECT sont autorisées
    
    Args:
        doc_id: ID du document
        sql_query: Requête SQL à exécuter (SELECT uniquement)
        parameters: Liste des paramètres pour les placeholders '?' dans la requête
        timeout_ms: Délai d'expiration en millisecondes (défaut: 1000)
        
    Returns:
        Dict avec les résultats de la requête et métadonnées
    """
    logger.info(f"Tool called: execute_sql_query for doc_id: {doc_id}")
    
    try:
        # Vérifier que la requête est une requête SELECT
        sql_query = sql_query.strip()
        if not re.match(r'^SELECT\s', sql_query, re.IGNORECASE):
            return {
                "success": False,
                "message": "Seules les requêtes SELECT sont autorisées pour des raisons de sécurité.",
                "query": sql_query,
                "records": [],
                "record_count": 0
            }
        
        client = get_client(ctx)
        if not client:
            return {
                "success": False,
                "message": "Client Grist non configuré",
                "query": sql_query,
                "records": [],
                "record_count": 0
            }
        
        # Préparer la requête SQL
        query_data = {
            "sql": sql_query,
            "args": parameters or []
        }
        
        if timeout_ms:
            query_data["timeout"] = timeout_ms
        
        # Exécuter la requête SQL
        response = await client._request(
            method="POST",
            endpoint=f"/docs/{doc_id}/sql",
            json_data=query_data
        )
        
        # Extraire et formater les résultats
        statement = response.get("statement", sql_query)
        records = response.get("records", [])
        
        # Ajouter des IDs si nécessaire
        for i, record in enumerate(records):
            if "id" not in record:
                record["id"] = i + 1
        
        return {
            "success": True,
            "message": f"Requête SQL exécutée avec succès. {len(records)} enregistrements trouvés.",
            "query": sql_query,
            "statement": statement,
            "records": records,
            "record_count": len(records)
        }
        
    except Exception as e:
        logger.error(f"Error in execute_sql_query: {str(e)}")
        return {
            "success": False,
            "message": f"Erreur lors de l'exécution de la requête SQL: {str(e)}",
            "query": sql_query,
            "records": [],
            "record_count": 0
        }
