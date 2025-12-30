"""
Client pour l'API Grist.

Ce module fournit une classe client pour interagir avec l'API Grist,
facilitant les opérations CRUD sur les organisations, espaces de travail,
documents, tables, colonnes et enregistrements.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import httpx
from dotenv import load_dotenv
from fastmcp import Context

from .models import GristColumn, GristDocument, GristOrg, GristRecord, GristTable, GristWorkspace
from .version import __version__

# Configurer le logger
logger = logging.getLogger("grist_mcp_server")

def mask_api_key(api_key: str) -> str:
    """Masquer la clé API pour les logs."""
    if len(api_key) > 10:
        return f"{api_key[:5]}...{api_key[-5:]}"
    return "[SET]"

class GristClient:
    """Client pour l'API Grist."""
    
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.debug(f"GristClient initialized with API URL: {api_url}")
        logger.debug(f"API key: {mask_api_key(api_key)}")
    
    async def _request(self, 
                      method: str, 
                      endpoint: str, 
                      json_data: Optional[Dict[str, Any]] = None,
                      params: Optional[Dict[str, Any]] = None) -> Any:
        """Effectue une requête à l'API Grist."""
        # Fix URL construction: ensure endpoint starts with / and base URL doesn't end with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        api_url = self.api_url.rstrip('/')
        url = api_url + endpoint
        
        logger.debug(f"Making {method} request to {url}")
        if params:
            logger.debug(f"Params: {params}")
        if json_data:
            logger.debug(f"JSON data: {json.dumps(json_data)[:200]}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:  # Set a reasonable timeout
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=json_data,
                    params=params
                )
                
                logger.debug(f"Response status: {response.status_code}")
                
                if response.status_code >= 400:
                    logger.error(f"Error response: {response.text}")
                    logger.error(f"URL that failed: {url}")
                
                response.raise_for_status()
                
                # Log first part of response for debugging
                json_response = response.json()
                logger.debug(f"Response preview: {str(json_response)[:200]}...")
                return json_response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            logger.error(f"Failed URL: {url}")
            logger.error(f"Response text: {e.response.text}")
            raise ValueError(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            logger.error(f"Failed URL: {url}")
            raise ValueError(f"Request error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.error(f"Failed URL: {url}")
            raise ValueError(f"Unexpected error: {str(e)}")
    
    # --- Organisation Methods ---
    
    async def list_orgs(self) -> List[GristOrg]:
        """Liste toutes les organisations accessibles."""
        logger.debug("Listing organizations")
        data = await self._request("GET", "/orgs")
        
        # Check if the response is in the expected format
        if not isinstance(data, list):
            logger.warning(f"Unexpected response format: {data}")
            return []
        return [GristOrg(**org) for org in data]
    
    async def describe_org(self, org_id: Union[int, str]) -> Dict[str, Any]:
        """Obtient les détails d'une organisation spécifique."""
        logger.debug(f"Describing organization {org_id}")
        return await self._request("GET", f"/orgs/{org_id}")
    
    async def modify_org(self, org_id: Union[int, str], org_data: Dict[str, Any]) -> None:
        """Modifie une organisation."""
        logger.debug(f"Modifying organization {org_id}")
        await self._request("PATCH", f"/orgs/{org_id}", json_data=org_data)
    
    async def delete_org(self, org_id: Union[int, str]) -> None:
        """Supprime une organisation."""
        logger.debug(f"Deleting organization {org_id}")
        await self._request("DELETE", f"/orgs/{org_id}")
    
    # --- Workspace Methods ---
    
    async def list_workspaces(self, org_id: Union[int, str]) -> List[GristWorkspace]:
        """Liste tous les espaces de travail d'une organisation."""
        logger.debug(f"Listing workspaces for org {org_id}")
        data = await self._request("GET", f"/orgs/{org_id}/workspaces")
        
        # Check if the response is in the expected format
        if not isinstance(data, list):
            logger.warning(f"Unexpected response format for workspaces: {data}")
            return []
            
        return [GristWorkspace(**workspace) for workspace in data]
    
    async def describe_workspace(self, workspace_id: int) -> Dict[str, Any]:
        """Obtient les détails d'un espace de travail spécifique."""
        logger.debug(f"Describing workspace {workspace_id}")
        return await self._request("GET", f"/workspaces/{workspace_id}")
    
    async def create_workspace(self, org_id: Union[int, str], workspace_data: Dict[str, Any]) -> int:
        """Crée un nouvel espace de travail dans une organisation."""
        logger.debug(f"Creating workspace in organization {org_id}")
        result = await self._request("POST", f"/orgs/{org_id}/workspaces", json_data=workspace_data)
        return result
    
    async def modify_workspace(self, workspace_id: int, workspace_data: Dict[str, Any]) -> None:
        """Modifie un espace de travail."""
        logger.debug(f"Modifying workspace {workspace_id}")
        await self._request("PATCH", f"/workspaces/{workspace_id}", json_data=workspace_data)
    
    async def delete_workspace(self, workspace_id: int) -> None:
        """Supprime un espace de travail."""
        logger.debug(f"Deleting workspace {workspace_id}")
        await self._request("DELETE", f"/workspaces/{workspace_id}")
    
    # --- Document Methods ---
    
    async def list_documents(self, workspace_id: int) -> List[GristDocument]:
        """Liste tous les documents d'un espace de travail."""
        logger.debug(f"Listing documents for workspace {workspace_id}")
        data = await self._request("GET", f"/workspaces/{workspace_id}")

        # Check if the expected 'docs' key exists
        if "docs" not in data:
            logger.warning(f"No 'docs' key found in workspace data: {data}")
            return []
            
        docs = data.get("docs", [])
        return [GristDocument(**doc) for doc in docs]
    
    async def describe_doc(self, doc_id: str) -> Dict[str, Any]:
        """Obtient les détails d'un document spécifique."""
        logger.debug(f"Describing document {doc_id}")
        return await self._request("GET", f"/docs/{doc_id}")
    
    async def create_doc(self, workspace_id: int, doc_data: Dict[str, Any]) -> str:
        """Crée un nouveau document dans un espace de travail."""
        logger.debug(f"Creating document in workspace {workspace_id}")
        result = await self._request("POST", f"/workspaces/{workspace_id}/docs", json_data=doc_data)
        return result
    
    async def modify_doc(self, doc_id: str, doc_data: Dict[str, Any]) -> None:
        """Modifie un document."""
        logger.debug(f"Modifying document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}", json_data=doc_data)
    
    async def delete_doc(self, doc_id: str) -> None:
        """Supprime un document."""
        logger.debug(f"Deleting document {doc_id}")
        await self._request("DELETE", f"/docs/{doc_id}")
    
    async def move_doc(self, doc_id: str, target_workspace_id: int) -> None:
        """Déplace un document vers un autre espace de travail."""
        logger.debug(f"Moving document {doc_id} to workspace {target_workspace_id}")
        await self._request("PATCH", f"/docs/{doc_id}/move", json_data={"workspace": target_workspace_id})

    # --- Table Methods ---
    
    async def list_tables(self, doc_id: str) -> List[GristTable]:
        """Liste toutes les tables d'un document."""
        logger.debug(f"Listing tables for document {doc_id}")
        data = await self._request("GET", f"/docs/{doc_id}/tables")
        return [GristTable(**table) for table in data.get("tables", [])]
    
    async def create_tables(self, doc_id: str, tables_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Crée de nouvelles tables dans un document."""
        logger.debug(f"Creating tables in document {doc_id}")
        result = await self._request("POST", f"/docs/{doc_id}/tables", json_data=tables_data)
        return result.get("tables", [])
    
    async def modify_tables(self, doc_id: str, tables_data: Dict[str, Any]) -> None:
        """Modifie des tables dans un document."""
        logger.debug(f"Modifying tables in document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}/tables", json_data=tables_data)

    # --- Column Methods ---
    
    async def list_columns(self, doc_id: str, table_id: str) -> List[GristColumn]:
        """Liste toutes les colonnes d'une table."""
        logger.debug(f"Listing columns for table {table_id} in document {doc_id}")
        data = await self._request("GET", f"/docs/{doc_id}/tables/{table_id}/columns")
        return [GristColumn(**column) for column in data.get("columns", [])]
    
    async def create_columns(self, doc_id: str, table_id: str, columns_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Crée de nouvelles colonnes dans une table."""
        logger.debug(f"Creating columns in table {table_id} of document {doc_id}")
        result = await self._request("POST", f"/docs/{doc_id}/tables/{table_id}/columns", json_data=columns_data)
        return result.get("columns", [])
    
    async def modify_columns(self, doc_id: str, table_id: str, columns_data: Dict[str, Any]) -> None:
        """Modifie des colonnes dans une table."""
        logger.debug(f"Modifying columns in table {table_id} of document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}/tables/{table_id}/columns", json_data=columns_data)
    
    async def replace_columns(self, doc_id: str, table_id: str, columns_data: Dict[str, Any], 
                            noadd: bool = False, noupdate: bool = False, replaceall: bool = False) -> None:
        """Remplace des colonnes dans une table."""
        params = {}
        if noadd:
            params["noadd"] = "true"
        if noupdate:
            params["noupdate"] = "true"
        if replaceall:
            params["replaceall"] = "true"
        
        logger.debug(f"Replacing columns in table {table_id} of document {doc_id}")
        await self._request("PUT", f"/docs/{doc_id}/tables/{table_id}/columns", 
                          json_data=columns_data, params=params)
    
    async def delete_column(self, doc_id: str, table_id: str, col_id: str) -> None:
        """Supprime une colonne d'une table."""
        logger.debug(f"Deleting column {col_id} from table {table_id} in document {doc_id}")
        await self._request("DELETE", f"/docs/{doc_id}/tables/{table_id}/columns/{col_id}")

    # --- Record Methods ---
    
    async def list_records(self, doc_id: str, table_id: str, 
                        sort: Optional[str] = None,
                        limit: Optional[int] = None) -> List[GristRecord]:
        """Liste les enregistrements d'une table avec tri et limite optionnels."""
        params = {}
        if sort:
            params["sort"] = sort
        if limit and limit > 0:
            params["limit"] = limit
        
        logger.debug(f"Listing records for table {table_id} in document {doc_id} with params: {params}")    
        data = await self._request(
            "GET", 
            f"/docs/{doc_id}/tables/{table_id}/records",
            params=params
        )
        return [GristRecord(**record) for record in data.get("records", [])]
    
    async def add_records(self, doc_id: str, table_id: str, 
                        records: List[Dict[str, Any]]) -> List[int]:
        """Ajoute des enregistrements à une table."""
        # Verify input data format
        if all("fields" in record for record in records):
            # Data is already in the expected API format
            formatted_records = {"records": records}
            logger.debug("Records already in expected format")
        else:
            # Transform data to expected API format
            formatted_records = {"records": [{"fields": record} for record in records]}
            logger.debug("Transforming records to expected format")
        
        logger.debug(f"Adding records to table {table_id} in document {doc_id}")
        
        data = await self._request(
            "POST",
            f"/docs/{doc_id}/tables/{table_id}/records",
            json_data=formatted_records
        )
        return [record["id"] for record in data.get("records", [])]
    
    async def update_records(self, doc_id: str, table_id: str, 
                          records: List[Dict[str, Any]]) -> List[int]:
        """Met à jour des enregistrements dans une table."""
        # Verify input data format
        if all(isinstance(record, dict) and "id" in record and "fields" in record for record in records):
            # Data is already in the expected API format
            formatted_records = {"records": records}
            logger.debug("Records already in expected format")
        else:
            # Assume entries are in format [{"id": 1, ...fields...}, {"id": 2, ...fields...}]
            formatted_records = {"records": []}
            for record in records:
                if "id" not in record:
                    raise ValueError(f"Each record must contain an 'id' field: {record}")
                
                record_id = record.pop("id")
                formatted_record = {
                    "id": record_id,
                    "fields": record
                }
                formatted_records["records"].append(formatted_record)
            logger.debug("Transforming records to expected format")
        
        logger.debug(f"Updating records in table {table_id} in document {doc_id}")
        
        data = await self._request(
            "PATCH",
            f"/docs/{doc_id}/tables/{table_id}/records",
            json_data=formatted_records
        )
        
        # Handle response based on API format
        if data is None:
            # If API returns nothing, return provided IDs
            logger.info("Empty response received from API, using provided IDs")
            return [record["id"] for record in formatted_records["records"]]
        elif "records" in data and isinstance(data["records"], list):
            # If API returns records, extract IDs
            return [record["id"] for record in data["records"]]
        else:
            # If structure is not recognized, log and return provided IDs
            logger.warning(f"Unexpected response format: {data}")
            return [record["id"] for record in formatted_records["records"]]
    
    async def delete_records(self, doc_id: str, table_id: str, record_ids: List[int]) -> None:
        """Supprime des enregistrements d'une table."""
        logger.debug(f"Deleting records with IDs {record_ids} from table {table_id} in document {doc_id}")
        
        # L'API Grist attend un tableau d'IDs directement
        await self._request(
            "POST",
            f"/docs/{doc_id}/tables/{table_id}/data/delete",
            json_data=record_ids  # Envoi direct de la liste d'IDs
        )
        logger.debug(f"Successfully deleted {len(record_ids)} records")

    # --- Access Management Methods ---
    
    async def list_org_access(self, org_id: Union[int, str]) -> Dict[str, Any]:
        """Liste les utilisateurs ayant accès à une organisation."""
        logger.debug(f"Listing access for organization {org_id}")
        return await self._request("GET", f"/orgs/{org_id}/access")
    
    async def modify_org_access(self, org_id: Union[int, str], access_delta: Dict[str, Any]) -> None:
        """Modifie l'accès à une organisation."""
        logger.debug(f"Modifying access for organization {org_id}")
        await self._request("PATCH", f"/orgs/{org_id}/access", json_data={"delta": access_delta})
    
    async def list_workspace_access(self, workspace_id: int) -> Dict[str, Any]:
        """Liste les utilisateurs ayant accès à un espace de travail."""
        logger.debug(f"Listing access for workspace {workspace_id}")
        return await self._request("GET", f"/workspaces/{workspace_id}/access")
    
    async def modify_workspace_access(self, workspace_id: int, access_delta: Dict[str, Any]) -> None:
        """Modifie l'accès à un espace de travail."""
        logger.debug(f"Modifying access for workspace {workspace_id}")
        await self._request("PATCH", f"/workspaces/{workspace_id}/access", json_data={"delta": access_delta})
    
    async def list_doc_access(self, doc_id: str) -> Dict[str, Any]:
        """Liste les utilisateurs ayant accès à un document."""
        logger.debug(f"Listing access for document {doc_id}")
        return await self._request("GET", f"/docs/{doc_id}/access")
    
    async def modify_doc_access(self, doc_id: str, access_delta: Dict[str, Any]) -> None:
        """Modifie l'accès à un document."""
        logger.debug(f"Modifying access for document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}/access", json_data={"delta": access_delta})

    # --- Download and Export Methods ---
    
    async def download_doc(self, doc_id: str, nohistory: bool = False, template: bool = False) -> bytes:
        """Télécharge un document au format SQLite."""
        params = {}
        if nohistory:
            params["nohistory"] = "true"
        if template:
            params["template"] = "true"
        
        logger.debug(f"Downloading document {doc_id} as SQLite")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method="GET",
                url=f"{self.api_url.rstrip('/')}/docs/{doc_id}/download",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.content
    
    async def download_doc_xlsx(self, doc_id: str, header: str = "label") -> bytes:
        """Télécharge un document au format Excel."""
        params = {"header": header}
        
        logger.debug(f"Downloading document {doc_id} as Excel")
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:  # Augmenter timeout
                response = await client.request(
                    method="GET",
                    url=f"{self.api_url.rstrip('/')}/docs/{doc_id}/download/xlsx",
                    headers=self.headers,
                    params=params
                )
                
                logger.debug(f"Excel download response status: {response.status_code}")
                logger.debug(f"Excel download response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                return response.content
                
        except httpx.TimeoutException as e:
            logger.error(f"Excel download timeout for doc {doc_id}: {e}")
            raise ValueError(f"Excel download timeout - document may be too large. Try download_document_sqlite as alternative.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Excel download HTTP error for doc {doc_id}: {e}")
            logger.error(f"Response text: {e.response.text}")
            raise ValueError(f"Excel download failed: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Excel download unexpected error for doc {doc_id}: {e}")
            raise ValueError(f"Excel download failed: {str(e)}")
    
    async def download_doc_csv(self, doc_id: str, table_id: str, header: str = "label") -> str:
        """Télécharge une table au format CSV."""
        params = {"tableId": table_id, "header": header}
        
        logger.debug(f"Downloading table {table_id} from document {doc_id} as CSV")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method="GET",
                url=f"{self.api_url.rstrip('/')}/docs/{doc_id}/download/csv",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.text
    
    async def download_table_schema(self, doc_id: str, table_id: str, header: str = "label") -> Dict[str, Any]:
        """Télécharge le schéma d'une table."""
        params = {"tableId": table_id, "header": header}
        
        logger.debug(f"Downloading schema for table {table_id} from document {doc_id}")
        return await self._request("GET", f"/docs/{doc_id}/download/table-schema", params=params)

    # --- Document Management Methods ---
    
    async def force_reload_doc(self, doc_id: str) -> None:
        """Force le rechargement d'un document."""
        logger.debug(f"Force reloading document {doc_id}")
        await self._request("POST", f"/docs/{doc_id}/force-reload")
    
    async def delete_doc_history(self, doc_id: str, keep: int) -> None:
        """Supprime l'historique d'un document, ne conservant que les dernières actions."""
        logger.debug(f"Deleting history for document {doc_id}, keeping {keep} actions")
        await self._request("POST", f"/docs/{doc_id}/states/remove", json_data={"keep": keep})

    # --- Attachment Methods ---
    
    async def list_attachments(self, doc_id: str, sort: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Liste toutes les pièces jointes d'un document."""
        params = {}
        if sort:
            params["sort"] = sort
        if limit:
            params["limit"] = limit
        
        logger.debug(f"Listing attachments for document {doc_id}")
        data = await self._request("GET", f"/docs/{doc_id}/attachments", params=params)
        return data.get("records", [])
    
    async def get_attachment_metadata(self, doc_id: str, attachment_id: int) -> Dict[str, Any]:
        """Obtient les métadonnées d'une pièce jointe spécifique."""
        logger.debug(f"Getting metadata for attachment {attachment_id} in document {doc_id}")
        return await self._request("GET", f"/docs/{doc_id}/attachments/{attachment_id}")
    
    async def download_attachment(self, doc_id: str, attachment_id: int) -> bytes:
        """Télécharge le contenu d'une pièce jointe."""
        logger.debug(f"Downloading attachment {attachment_id} from document {doc_id}")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method="GET",
                url=f"{self.api_url.rstrip('/')}/docs/{doc_id}/attachments/{attachment_id}/download",
                headers=self.headers
            )
            response.raise_for_status()
            return response.content
    
    async def upload_attachments(self, doc_id: str, files: List[tuple]) -> List[int]:
        """Téléverse des pièces jointes dans un document."""
        logger.debug(f"Uploading {len(files)} attachments to document {doc_id}")
        
        # Prepare multipart form data
        files_data = []
        for filename, content, content_type in files:
            files_data.append(('upload', (filename, content, content_type)))
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.request(
                method="POST",
                url=f"{self.api_url.rstrip('/')}/docs/{doc_id}/attachments",
                headers={k: v for k, v in self.headers.items() if k != "Content-Type"},  # Remove Content-Type for multipart
                files=files_data
            )
            response.raise_for_status()
            data = response.json()
            return data

    # --- Webhook Methods ---
    
    async def list_webhooks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Liste tous les webhooks d'un document."""
        logger.debug(f"Listing webhooks for document {doc_id}")
        data = await self._request("GET", f"/docs/{doc_id}/webhooks")
        return data.get("webhooks", [])
    
    async def create_webhooks(self, doc_id: str, webhooks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Crée de nouveaux webhooks pour un document."""
        logger.debug(f"Creating {len(webhooks)} webhooks for document {doc_id}")
        webhook_data = {"webhooks": [{"fields": webhook} for webhook in webhooks]}
        data = await self._request("POST", f"/docs/{doc_id}/webhooks", json_data=webhook_data)
        return data.get("webhooks", [])
    
    async def modify_webhook(self, doc_id: str, webhook_id: str, webhook_data: Dict[str, Any]) -> None:
        """Modifie un webhook."""
        logger.debug(f"Modifying webhook {webhook_id} for document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}/webhooks/{webhook_id}", json_data=webhook_data)
    
    async def delete_webhook(self, doc_id: str, webhook_id: str) -> Dict[str, Any]:
        """Supprime un webhook."""
        logger.debug(f"Deleting webhook {webhook_id} for document {doc_id}")
        return await self._request("DELETE", f"/docs/{doc_id}/webhooks/{webhook_id}")
    
    async def clear_webhook_queue(self, doc_id: str) -> None:
        """Vide la file d'attente des webhooks pour un document."""
        logger.debug(f"Clearing webhook queue for document {doc_id}")
        await self._request("DELETE", f"/docs/{doc_id}/webhooks/queue")

    # --- Helper Methods for Validation and Error Enhancement ---
    
    async def validate_table_exists(self, doc_id: str, table_id: str) -> Dict[str, Any]:
        """Valide si une table existe et retourne des informations utiles si ce n'est pas le cas."""
        try:
            tables = await self.list_tables(doc_id)
            table_ids = [table.id for table in tables]
            
            if table_id not in table_ids:
                # Find closest match
                import difflib
                closest = difflib.get_close_matches(table_id, table_ids, n=1, cutoff=0.6)
                return {
                    "exists": False,
                    "error": f"Table '{table_id}' not found in document {doc_id}",
                    "available_tables": table_ids,
                    "suggestion": closest[0] if closest else None
                }
            return {"exists": True}
        except Exception as e:
            return {"exists": False, "error": f"Could not validate table: {str(e)}"}
    
    async def validate_columns_exist(self, doc_id: str, table_id: str, column_names: List[str]) -> Dict[str, Any]:
        """Valide si des colonnes existent et retourne des informations utiles si ce n'est pas le cas."""
        try:
            columns = await self.list_columns(doc_id, table_id)
            available_columns = [col.id for col in columns]
            column_labels = {col.fields.get('label', col.id): col.id for col in columns}
            
            missing_columns = []
            suggestions = {}
            
            for col_name in column_names:
                if col_name not in available_columns:
                    # Check if it's a label instead of ID
                    if col_name in column_labels:
                        suggestions[col_name] = {
                            "type": "label_vs_id",
                            "suggestion": column_labels[col_name],
                            "message": f"Use column ID '{column_labels[col_name]}' instead of label '{col_name}'"
                        }
                    else:
                        # Find closest match
                        import difflib
                        closest = difflib.get_close_matches(col_name, available_columns, n=1, cutoff=0.6)
                        missing_columns.append(col_name)
                        if closest:
                            suggestions[col_name] = {
                                "type": "typo",
                                "suggestion": closest[0],
                                "message": f"Did you mean '{closest[0]}'?"
                            }
            
            if missing_columns or suggestions:
                return {
                    "valid": False,
                    "missing_columns": missing_columns,
                    "suggestions": suggestions,
                    "available_columns": available_columns,
                    "column_labels": column_labels
                }
            
            return {"valid": True}
        except Exception as e:
            return {"valid": False, "error": f"Could not validate columns: {str(e)}"}
    
    async def get_formula_column_map(self, doc_id: str, table_id: str) -> Dict[str, Any]:
        """Obtient un mappage pour la construction de formules avec des références de colonnes appropriées."""
        try:
            columns = await self.list_columns(doc_id, table_id)
            
            formula_map = {
                "columns": [],
                "id_to_label": {},
                "label_to_id": {},
                "formula_references": {},
                "case_variants": {}
            }
            
            for col in columns:
                col_id = col.id
                col_label = col.fields.get('label', col_id)
                
                # Mappings de base
                formula_map["columns"].append({
                    "id": col_id,
                    "label": col_label,
                    "type": col.fields.get('type', 'Text'),
                    "formula_ref": f"${col_id}"
                })
                
                formula_map["id_to_label"][col_id] = col_label
                formula_map["label_to_id"][col_label] = col_id
                formula_map["formula_references"][col_label] = f"${col_id}"
                
                # Variantes de casse pour détection d'erreurs
                formula_map["case_variants"][col_id.lower()] = col_id
                formula_map["case_variants"][col_label.lower()] = col_id
            
            return formula_map
        except Exception as e:
            return {"error": f"Could not generate formula map: {str(e)}"}
    
    async def validate_formula_syntax(self, doc_id: str, table_id: str, formula: str) -> Dict[str, Any]:
        """Valide la syntaxe d'une formule et suggère des corrections."""
        try:
            formula_map = await self.get_formula_column_map(doc_id, table_id)
            if "error" in formula_map:
                return formula_map
            
            import re
            
            # Extraire les références de colonnes dans la formule
            column_refs = re.findall(r'\$([A-Za-z_][A-Za-z0-9_]*)', formula)
            
            issues = []
            suggestions = []
            corrected_formula = formula
            
            for ref in column_refs:
                # Vérifier si la référence existe exactement
                if ref not in formula_map["id_to_label"]:
                    # Chercher des variantes de casse
                    ref_lower = ref.lower()
                    if ref_lower in formula_map["case_variants"]:
                        correct_ref = formula_map["case_variants"][ref_lower]
                        issues.append({
                            "type": "case_error",
                            "found": f"${ref}",
                            "correct": f"${correct_ref}",
                            "message": f"Case mismatch: use ${correct_ref} instead of ${ref}"
                        })
                        corrected_formula = corrected_formula.replace(f"${ref}", f"${correct_ref}")
                    else:
                        # Chercher des correspondances approximatives
                        import difflib
                        available_ids = list(formula_map["id_to_label"].keys())
                        closest = difflib.get_close_matches(ref, available_ids, n=1, cutoff=0.6)
                        
                        issues.append({
                            "type": "unknown_column",
                            "found": f"${ref}",
                            "message": f"Column ${ref} not found",
                            "suggestion": f"${closest[0]}" if closest else None,
                            "available_columns": [f"${col_id}" for col_id in available_ids]
                        })
            
            return {
                "valid": len(issues) == 0,
                "original_formula": formula,
                "corrected_formula": corrected_formula if corrected_formula != formula else None,
                "issues": issues,
                "formula_map": formula_map
            }
            
        except Exception as e:
            return {"valid": False, "error": f"Could not validate formula: {str(e)}"}


def get_client(ctx: Context = None) -> GristClient:
    """
    Obtient un client Grist configuré.
    
    Args:
        ctx: Contexte MCP optionnel.
        
    Returns:
        Une instance configurée de GristClient.
        
    Raises:
        ValueError: Si la variable d'environnement GRIST_API_KEY n'est pas définie.
    """
    # Charger les variables d'environnement
    load_dotenv()
    
    api_key = os.environ.get("GRIST_API_KEY", "")
    api_url = os.environ.get("GRIST_API_URL", os.environ.get("GRIST_API_HOST", "https://docs.getgrist.com/api"))
    
    if not api_key:
        raise ValueError("GRIST_API_KEY environment variable is not set")
    
    # Ensure the URL is properly formatted
    if not api_url.startswith("http"):
        api_url = "https://" + api_url
    
    logger.debug(f"Creating Grist client with API URL: {api_url}")
    return GristClient(api_key=api_key, api_url=api_url)
