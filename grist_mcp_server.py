#!/usr/bin/env python3
"""
Grist MCP Server - Provides MCP tools for interacting with Grist API

This server implements the Model Context Protocol (MCP) for Grist,
enabling language models to interact with Grist spreadsheets.
"""

import json
import os
import logging
import sys
from typing import List, Dict, Any, Optional, Union

import httpx
from pydantic import BaseModel, Field, AnyHttpUrl
from dotenv import load_dotenv

try:
    # Import pour la nouvelle structure de packages
    from fastmcp import FastMCP, Context
except ImportError:
    try:
        # Fallback pour l'ancien mcp.server.fastmcp
        from mcp.server.fastmcp import FastMCP, Context
    except ImportError:
        print("Error: fastmcp or mcp packages not found. Please install them with: pip install fastmcp mcp")
        sys.exit(1)

# Version
__version__ = "1.0.0"

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
log_levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
level = log_levels.get(log_level, logging.INFO)

logging.basicConfig(
    level=level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("grist_mcp_server.log", mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("grist_mcp_server")

# Load environment variables from .env file
load_dotenv()

# Mask sensitive information
def mask_api_key(api_key: str) -> str:
    """Mask the API key for logging purposes"""
    if len(api_key) > 10:
        return f"{api_key[:5]}...{api_key[-5:]}"
    return "[SET]"

# Create the MCP server with explicit name and instructions
mcp = FastMCP(
    name="Grist API Client",
    version=__version__,
    dependencies=["httpx", "pydantic", "python-dotenv"],
    description="Serveur MCP pour l'API Grist",
    stateless_http=True,  # Support pour le mode stateless HTTP
    instructions="""
    Vous êtes un assistant spécialisé dans l'interaction avec l'API Grist.
    Vous pouvez utiliser les outils suivants pour interagir avec les données Grist :

    1. Outils de listing :
       - list_organizations : Liste toutes les organisations Grist accessibles
       - list_workspaces : Liste les espaces de travail dans une organisation
       - list_documents : Liste les documents dans un espace de travail
       - list_tables : Liste les tables dans un document
       - list_columns : Liste les colonnes dans une table
       - list_records : Liste les enregistrements dans une table

    2. Outils de gestion des enregistrements :
       - add_grist_records : Ajoute des enregistrements à une table
       - update_grist_records : Met à jour des enregistrements existants
       - delete_grist_records : Supprime des enregistrements

    3. Outils SQL pour le filtrage :
       - filter_sql_query : Requête SQL optimisée pour le filtrage
         * Utilisez pour les cas simples de filtrage
         * Exemple : filter_sql_query(doc_id="doc", table_id="table", 
                                    where_conditions={"organisation": "OPSIA"})
         * Supporte le tri et la limitation des résultats
       
       - execute_sql_query : Requête SQL générale
         * Utilisez pour les requêtes complexes
         * Exemple : execute_sql_query(doc_id="doc", 
                                     sql_query="SELECT * FROM Table WHERE status = ?",
                                     parameters=["actif"])
         * Supporte les paramètres et le timeout

    Notes d'utilisation importantes :

    1. Pour le filtrage des données :
       - Utilisez filter_sql_query pour les filtres simples
       - Utilisez execute_sql_query pour les requêtes complexes
       - Les deux fonctions retournent les mêmes informations

    2. Pour la suppression d'enregistrements (delete_grist_records) :
       - Les IDs des enregistrements doivent être des entiers
       - Fournissez toujours une liste d'IDs valides
       - Vérifiez les IDs avant la suppression

    3. Pour les requêtes SQL :
       - Seules les requêtes SELECT sont autorisées
       - Utilisez des paramètres pour éviter les injections SQL
       - Le timeout par défaut est de 1000ms

    4. Pour la gestion des erreurs :
       - Tous les outils retournent un statut success/error
       - Les messages d'erreur sont détaillés
       - Consultez les logs pour plus d'informations

    5. Bonnes pratiques :
       - Privilégiez filter_sql_query pour le filtrage simple
       - Utilisez execute_sql_query pour les requêtes complexes
       - Vérifiez toujours les IDs avant les opérations
       - Utilisez les paramètres SQL pour la sécurité
       - Gérez les erreurs de manière appropriée
       - Consultez la documentation pour les formats de données
    """
)

# Configuration
class GristConfig(BaseModel):
    """Configuration for Grist API client"""
    api_key: str = Field(..., description="Grist API Key")
    api_url: AnyHttpUrl = Field(default="https://docs.getgrist.com/api")

# Models
class GristOrg(BaseModel):
    """Grist organization model"""
    id: int
    name: str
    domain: Optional[str] = None

class GristWorkspace(BaseModel):
    """Grist workspace model"""
    id: int
    name: str

class GristDocument(BaseModel):
    """Grist document model"""
    id: str
    name: str
    
class GristTable(BaseModel):
    """Grist table model"""
    id: str
    
class GristColumn(BaseModel):
    """Grist column model"""
    id: str
    fields: Dict[str, Any]

class GristRecord(BaseModel):
    """Grist record model"""
    id: int
    fields: Dict[str, Any]

# Client
class GristClient:
    """Client for the Grist API"""
    
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
        """Make a request to the Grist API"""
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
                if level == logging.DEBUG:
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
    
    async def list_orgs(self) -> List[GristOrg]:
        """List all organizations the user has access to"""
        logger.debug("Listing organizations")
        data = await self._request("GET", "/orgs")
        
        # Check if the response is in the expected format
        if not isinstance(data, list):
            logger.warning(f"Unexpected response format: {data}")
            return []
        return [GristOrg(**org) for org in data]
    
    async def list_workspaces(self, org_id: Union[int, str]) -> List[GristWorkspace]:
        """List all workspaces in an organization"""
        logger.debug(f"Listing workspaces for org {org_id}")
        data = await self._request("GET", f"/orgs/{org_id}/workspaces")
        
        # Check if the response is in the expected format
        if not isinstance(data, list):
            logger.warning(f"Unexpected response format for workspaces: {data}")
            return []
            
        return [GristWorkspace(**workspace) for workspace in data]
    
    async def list_documents(self, workspace_id: int) -> List[GristDocument]:
        """List all documents in a workspace"""
        logger.debug(f"Listing documents for workspace {workspace_id}")
        data = await self._request("GET", f"/workspaces/{workspace_id}")
        
        # Check if the expected 'docs' key exists
        if "docs" not in data:
            logger.warning(f"No 'docs' key found in workspace data: {data}")
            return []
            
        docs = data.get("docs", [])
        return [GristDocument(**doc) for doc in docs]
    
    async def list_tables(self, doc_id: str) -> List[GristTable]:
        """List all tables in a document"""
        logger.debug(f"Listing tables for document {doc_id}")
        data = await self._request("GET", f"/docs/{doc_id}/tables")
        return [GristTable(**table) for table in data.get("tables", [])]
    
    async def list_columns(self, doc_id: str, table_id: str) -> List[GristColumn]:
        """List all columns in a table"""
        logger.debug(f"Listing columns for table {table_id} in document {doc_id}")
        data = await self._request("GET", f"/docs/{doc_id}/tables/{table_id}/columns")
        return [GristColumn(**column) for column in data.get("columns", [])]
    
    async def list_records(self, doc_id: str, table_id: str, 
                        sort: Optional[str] = None,
                        limit: Optional[int] = None) -> List[GristRecord]:
        """List records in a table with optional sorting and limiting"""
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
        """Add records to a table"""
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
        """Update records in a table"""
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
        """Delete records from a table"""
        logger.debug(f"Deleting records with IDs {record_ids} from table {table_id} in document {doc_id}")
        
        # L'API Grist attend un tableau d'IDs directement
        await self._request(
            "POST",
            f"/docs/{doc_id}/tables/{table_id}/data/delete",
            json_data=record_ids  # Envoi direct de la liste d'IDs
        )
        logger.debug(f"Successfully deleted {len(record_ids)} records")

    # CRUD Operations for Organizations
    async def describe_org(self, org_id: Union[int, str]) -> Dict[str, Any]:
        """Get details of a specific organization"""
        logger.debug(f"Describing organization {org_id}")
        return await self._request("GET", f"/orgs/{org_id}")
    
    async def modify_org(self, org_id: Union[int, str], org_data: Dict[str, Any]) -> None:
        """Modify an organization"""
        logger.debug(f"Modifying organization {org_id}")
        await self._request("PATCH", f"/orgs/{org_id}", json_data=org_data)
    
    async def delete_org(self, org_id: Union[int, str]) -> None:
        """Delete an organization"""
        logger.debug(f"Deleting organization {org_id}")
        await self._request("DELETE", f"/orgs/{org_id}")

    # CRUD Operations for Workspaces
    async def describe_workspace(self, workspace_id: int) -> Dict[str, Any]:
        """Get details of a specific workspace"""
        logger.debug(f"Describing workspace {workspace_id}")
        return await self._request("GET", f"/workspaces/{workspace_id}")
    
    async def create_workspace(self, org_id: Union[int, str], workspace_data: Dict[str, Any]) -> int:
        """Create a new workspace in an organization"""
        logger.debug(f"Creating workspace in organization {org_id}")
        result = await self._request("POST", f"/orgs/{org_id}/workspaces", json_data=workspace_data)
        return result
    
    async def modify_workspace(self, workspace_id: int, workspace_data: Dict[str, Any]) -> None:
        """Modify a workspace"""
        logger.debug(f"Modifying workspace {workspace_id}")
        await self._request("PATCH", f"/workspaces/{workspace_id}", json_data=workspace_data)
    
    async def delete_workspace(self, workspace_id: int) -> None:
        """Delete a workspace"""
        logger.debug(f"Deleting workspace {workspace_id}")
        await self._request("DELETE", f"/workspaces/{workspace_id}")

    # CRUD Operations for Documents
    async def describe_doc(self, doc_id: str) -> Dict[str, Any]:
        """Get details of a specific document"""
        logger.debug(f"Describing document {doc_id}")
        return await self._request("GET", f"/docs/{doc_id}")
    
    async def create_doc(self, workspace_id: int, doc_data: Dict[str, Any]) -> str:
        """Create a new document in a workspace"""
        logger.debug(f"Creating document in workspace {workspace_id}")
        result = await self._request("POST", f"/workspaces/{workspace_id}/docs", json_data=doc_data)
        return result
    
    async def modify_doc(self, doc_id: str, doc_data: Dict[str, Any]) -> None:
        """Modify a document"""
        logger.debug(f"Modifying document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}", json_data=doc_data)
    
    async def delete_doc(self, doc_id: str) -> None:
        """Delete a document"""
        logger.debug(f"Deleting document {doc_id}")
        await self._request("DELETE", f"/docs/{doc_id}")
    
    async def move_doc(self, doc_id: str, target_workspace_id: int) -> None:
        """Move a document to another workspace"""
        logger.debug(f"Moving document {doc_id} to workspace {target_workspace_id}")
        await self._request("PATCH", f"/docs/{doc_id}/move", json_data={"workspace": target_workspace_id})

    # CRUD Operations for Tables
    async def create_tables(self, doc_id: str, tables_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create new tables in a document"""
        logger.debug(f"Creating tables in document {doc_id}")
        result = await self._request("POST", f"/docs/{doc_id}/tables", json_data=tables_data)
        return result.get("tables", [])
    
    async def modify_tables(self, doc_id: str, tables_data: Dict[str, Any]) -> None:
        """Modify tables in a document"""
        logger.debug(f"Modifying tables in document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}/tables", json_data=tables_data)

    # CRUD Operations for Columns
    async def create_columns(self, doc_id: str, table_id: str, columns_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create new columns in a table"""
        logger.debug(f"Creating columns in table {table_id} of document {doc_id}")
        result = await self._request("POST", f"/docs/{doc_id}/tables/{table_id}/columns", json_data=columns_data)
        return result.get("columns", [])
    
    async def modify_columns(self, doc_id: str, table_id: str, columns_data: Dict[str, Any]) -> None:
        """Modify columns in a table"""
        logger.debug(f"Modifying columns in table {table_id} of document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}/tables/{table_id}/columns", json_data=columns_data)
    
    async def replace_columns(self, doc_id: str, table_id: str, columns_data: Dict[str, Any], 
                            noadd: bool = False, noupdate: bool = False, replaceall: bool = False) -> None:
        """Replace columns in a table (add or update)"""
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
        """Delete a column from a table"""
        logger.debug(f"Deleting column {col_id} from table {table_id} in document {doc_id}")
        await self._request("DELETE", f"/docs/{doc_id}/tables/{table_id}/columns/{col_id}")

    # Access Management Operations
    async def list_org_access(self, org_id: Union[int, str]) -> Dict[str, Any]:
        """List users with access to an organization"""
        logger.debug(f"Listing access for organization {org_id}")
        return await self._request("GET", f"/orgs/{org_id}/access")
    
    async def modify_org_access(self, org_id: Union[int, str], access_delta: Dict[str, Any]) -> None:
        """Modify access to an organization"""
        logger.debug(f"Modifying access for organization {org_id}")
        await self._request("PATCH", f"/orgs/{org_id}/access", json_data={"delta": access_delta})
    
    async def list_workspace_access(self, workspace_id: int) -> Dict[str, Any]:
        """List users with access to a workspace"""
        logger.debug(f"Listing access for workspace {workspace_id}")
        return await self._request("GET", f"/workspaces/{workspace_id}/access")
    
    async def modify_workspace_access(self, workspace_id: int, access_delta: Dict[str, Any]) -> None:
        """Modify access to a workspace"""
        logger.debug(f"Modifying access for workspace {workspace_id}")
        await self._request("PATCH", f"/workspaces/{workspace_id}/access", json_data={"delta": access_delta})
    
    async def list_doc_access(self, doc_id: str) -> Dict[str, Any]:
        """List users with access to a document"""
        logger.debug(f"Listing access for document {doc_id}")
        return await self._request("GET", f"/docs/{doc_id}/access")
    
    async def modify_doc_access(self, doc_id: str, access_delta: Dict[str, Any]) -> None:
        """Modify access to a document"""
        logger.debug(f"Modifying access for document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}/access", json_data={"delta": access_delta})

    # Download and Export Operations
    async def download_doc(self, doc_id: str, nohistory: bool = False, template: bool = False) -> bytes:
        """Download document as SQLite file"""
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
        """Download document as Excel file"""
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
        """Download table as CSV"""
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
        """Download table schema"""
        params = {"tableId": table_id, "header": header}
        
        logger.debug(f"Downloading schema for table {table_id} from document {doc_id}")
        return await self._request("GET", f"/docs/{doc_id}/download/table-schema", params=params)
    
    async def force_reload_doc(self, doc_id: str) -> None:
        """Force reload a document"""
        logger.debug(f"Force reloading document {doc_id}")
        await self._request("POST", f"/docs/{doc_id}/force-reload")
    
    async def delete_doc_history(self, doc_id: str, keep: int) -> None:
        """Delete document history, keeping only the latest actions"""
        logger.debug(f"Deleting history for document {doc_id}, keeping {keep} actions")
        await self._request("POST", f"/docs/{doc_id}/states/remove", json_data={"keep": keep})

    # Attachment Operations
    async def list_attachments(self, doc_id: str, sort: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all attachments in a document"""
        params = {}
        if sort:
            params["sort"] = sort
        if limit:
            params["limit"] = limit
        
        logger.debug(f"Listing attachments for document {doc_id}")
        data = await self._request("GET", f"/docs/{doc_id}/attachments", params=params)
        return data.get("records", [])
    
    async def get_attachment_metadata(self, doc_id: str, attachment_id: int) -> Dict[str, Any]:
        """Get metadata for a specific attachment"""
        logger.debug(f"Getting metadata for attachment {attachment_id} in document {doc_id}")
        return await self._request("GET", f"/docs/{doc_id}/attachments/{attachment_id}")
    
    async def download_attachment(self, doc_id: str, attachment_id: int) -> bytes:
        """Download attachment content"""
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
        """Upload attachments to a document
        
        Args:
            doc_id: Document ID
            files: List of tuples (filename, content, content_type)
        """
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

    # Webhook Operations
    async def list_webhooks(self, doc_id: str) -> List[Dict[str, Any]]:
        """List all webhooks for a document"""
        logger.debug(f"Listing webhooks for document {doc_id}")
        data = await self._request("GET", f"/docs/{doc_id}/webhooks")
        return data.get("webhooks", [])
    
    async def create_webhooks(self, doc_id: str, webhooks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create new webhooks for a document"""
        logger.debug(f"Creating {len(webhooks)} webhooks for document {doc_id}")
        webhook_data = {"webhooks": [{"fields": webhook} for webhook in webhooks]}
        data = await self._request("POST", f"/docs/{doc_id}/webhooks", json_data=webhook_data)
        return data.get("webhooks", [])
    
    async def modify_webhook(self, doc_id: str, webhook_id: str, webhook_data: Dict[str, Any]) -> None:
        """Modify a webhook"""
        logger.debug(f"Modifying webhook {webhook_id} for document {doc_id}")
        await self._request("PATCH", f"/docs/{doc_id}/webhooks/{webhook_id}", json_data=webhook_data)
    
    async def delete_webhook(self, doc_id: str, webhook_id: str) -> Dict[str, Any]:
        """Delete a webhook"""
        logger.debug(f"Deleting webhook {webhook_id} for document {doc_id}")
        return await self._request("DELETE", f"/docs/{doc_id}/webhooks/{webhook_id}")
    
    async def clear_webhook_queue(self, doc_id: str) -> None:
        """Clear the webhook queue for a document"""
        logger.debug(f"Clearing webhook queue for document {doc_id}")
        await self._request("DELETE", f"/docs/{doc_id}/webhooks/queue")

    # Helper Methods for Validation and Error Enhancement
    async def validate_table_exists(self, doc_id: str, table_id: str) -> Dict[str, Any]:
        """Validate if table exists and return helpful info if not"""
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
        """Validate if columns exist and return helpful info if not"""
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
        """Get mapping for formula construction with proper column references"""
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
        """Validate formula syntax and suggest corrections"""
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


# Get configuration from environment variables
def get_client(ctx: Optional[Context] = None) -> GristClient:
    """Get a configured Grist client"""
    api_key = os.environ.get("GRIST_API_KEY", "")
    api_url = os.environ.get("GRIST_API_URL", os.environ.get("GRIST_API_HOST", "https://docs.getgrist.com/api"))
    
    if not api_key:
        raise ValueError("GRIST_API_KEY environment variable is not set")
    
    # Ensure the URL is properly formatted
    if not api_url.startswith("http"):
        api_url = "https://" + api_url
    
    logger.debug(f"Creating Grist client with API URL: {api_url}")
    return GristClient(api_key=api_key, api_url=api_url)


# MCP Tools
@mcp.tool()
async def list_organizations(ctx: Context) -> List[Dict[str, Any]]:
    """
    List all Grist organizations that the user has access to.
    
    Returns a list of organizations with their IDs, names, and domains.
    """
    logger.info("Tool called: list_organizations")
    client = get_client(ctx)
    orgs = await client.list_orgs()
    return [org.dict() for org in orgs]


@mcp.tool()
async def describe_organization(org_id: Union[int, str], ctx: Context) -> Dict[str, Any]:
    """
    Get detailed information about a specific organization.
    
    Args:
        org_id: The ID of the organization to describe
        
    Returns:
        Detailed information about the organization
    """
    logger.info(f"Tool called: describe_organization with org_id: {org_id}")
    client = get_client(ctx)
    return await client.describe_org(org_id)


@mcp.tool()
async def modify_organization(
    org_id: Union[int, str], 
    name: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modify an organization's properties.
    
    Args:
        org_id: The ID of the organization to modify
        name: New name for the organization (optional)
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: modify_organization with org_id: {org_id}")
    client = get_client(ctx)
    
    org_data = {}
    if name is not None:
        org_data["name"] = name
    
    if not org_data:
        return {
            "success": False,
            "message": "No modification data provided"
        }
    
    try:
        await client.modify_org(org_id, org_data)
        return {
            "success": True,
            "message": f"Organization {org_id} modified successfully"
        }
    except Exception as e:
        logger.error(f"Error modifying organization: {e}")
        return {
            "success": False,
            "message": f"Error modifying organization: {str(e)}"
        }


@mcp.tool()
async def delete_organization(org_id: Union[int, str], ctx: Context) -> Dict[str, Any]:
    """
    Delete an organization.
    
    Args:
        org_id: The ID of the organization to delete
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: delete_organization with org_id: {org_id}")
    client = get_client(ctx)
    
    try:
        await client.delete_org(org_id)
        return {
            "success": True,
            "message": f"Organization {org_id} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting organization: {e}")
        return {
            "success": False,
            "message": f"Error deleting organization: {str(e)}"
        }


@mcp.tool()
async def list_workspaces(org_id: Union[int, str], ctx: Context) -> List[Dict[str, Any]]:
    """
    List all workspaces in a Grist organization.
    
    Args:
        org_id: The ID of the organization to list workspaces for
        
    Returns:
        A list of workspaces with their IDs and names
    """
    logger.info(f"Tool called: list_workspaces with org_id: {org_id}")
    client = get_client(ctx)
    workspaces = await client.list_workspaces(org_id)
    return [workspace.dict() for workspace in workspaces]


@mcp.tool()
async def describe_workspace(workspace_id: int, ctx: Context) -> Dict[str, Any]:
    """
    Get detailed information about a specific workspace.
    
    Args:
        workspace_id: The ID of the workspace to describe
        
    Returns:
        Detailed information about the workspace
    """
    logger.info(f"Tool called: describe_workspace with workspace_id: {workspace_id}")
    client = get_client(ctx)
    return await client.describe_workspace(workspace_id)


@mcp.tool()
async def create_workspace(
    org_id: Union[int, str], 
    name: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a new workspace in an organization.
    
    Args:
        org_id: The ID of the organization to create the workspace in
        name: Name for the new workspace
        
    Returns:
        The ID of the created workspace and status
    """
    logger.info(f"Tool called: create_workspace with org_id: {org_id}, name: {name}")
    client = get_client(ctx)
    
    workspace_data = {"name": name}
    
    try:
        workspace_id = await client.create_workspace(org_id, workspace_data)
        return {
            "success": True,
            "message": f"Workspace '{name}' created successfully",
            "workspace_id": workspace_id
        }
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        return {
            "success": False,
            "message": f"Error creating workspace: {str(e)}"
        }


@mcp.tool()
async def modify_workspace(
    workspace_id: int, 
    name: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modify a workspace's properties.
    
    Args:
        workspace_id: The ID of the workspace to modify
        name: New name for the workspace (optional)
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: modify_workspace with workspace_id: {workspace_id}")
    client = get_client(ctx)
    
    workspace_data = {}
    if name is not None:
        workspace_data["name"] = name
    
    if not workspace_data:
        return {
            "success": False,
            "message": "No modification data provided"
        }
    
    try:
        await client.modify_workspace(workspace_id, workspace_data)
        return {
            "success": True,
            "message": f"Workspace {workspace_id} modified successfully"
        }
    except Exception as e:
        logger.error(f"Error modifying workspace: {e}")
        return {
            "success": False,
            "message": f"Error modifying workspace: {str(e)}"
        }


@mcp.tool()
async def delete_workspace(workspace_id: int, ctx: Context) -> Dict[str, Any]:
    """
    Delete a workspace.
    
    Args:
        workspace_id: The ID of the workspace to delete
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: delete_workspace with workspace_id: {workspace_id}")
    client = get_client(ctx)
    
    try:
        await client.delete_workspace(workspace_id)
        return {
            "success": True,
            "message": f"Workspace {workspace_id} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        return {
            "success": False,
            "message": f"Error deleting workspace: {str(e)}"
        }


@mcp.tool()
async def list_documents(workspace_id: int, ctx: Context) -> List[Dict[str, Any]]:
    """
    List all documents in a Grist workspace.
    
    Args:
        workspace_id: The ID of the workspace to list documents for
        
    Returns:
        A list of documents with their IDs and names
    """
    logger.info(f"Tool called: list_documents with workspace_id: {workspace_id}")
    client = get_client(ctx)
    documents = await client.list_documents(workspace_id)
    return [document.dict() for document in documents]


@mcp.tool()
async def describe_document(doc_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Get detailed information about a specific document.
    
    Args:
        doc_id: The ID of the document to describe
        
    Returns:
        Detailed information about the document
    """
    logger.info(f"Tool called: describe_document with doc_id: {doc_id}")
    client = get_client(ctx)
    return await client.describe_doc(doc_id)


@mcp.tool()
async def create_document(
    workspace_id: int, 
    name: str,
    is_pinned: bool = False,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a new document in a workspace.
    
    Args:
        workspace_id: The ID of the workspace to create the document in
        name: Name for the new document
        is_pinned: Whether the document should be pinned (default: False)
        
    Returns:
        The ID of the created document and status
    """
    logger.info(f"Tool called: create_document with workspace_id: {workspace_id}, name: {name}")
    client = get_client(ctx)
    
    doc_data = {
        "name": name,
        "isPinned": is_pinned
    }
    
    try:
        doc_id = await client.create_doc(workspace_id, doc_data)
        return {
            "success": True,
            "message": f"Document '{name}' created successfully",
            "document_id": doc_id
        }
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        return {
            "success": False,
            "message": f"Error creating document: {str(e)}"
        }


@mcp.tool()
async def modify_document(
    doc_id: str, 
    name: Optional[str] = None,
    is_pinned: Optional[bool] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modify a document's properties.
    
    Args:
        doc_id: The ID of the document to modify
        name: New name for the document (optional)
        is_pinned: Whether the document should be pinned (optional)
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: modify_document with doc_id: {doc_id}")
    client = get_client(ctx)
    
    doc_data = {}
    if name is not None:
        doc_data["name"] = name
    if is_pinned is not None:
        doc_data["isPinned"] = is_pinned
    
    if not doc_data:
        return {
            "success": False,
            "message": "No modification data provided"
        }
    
    try:
        await client.modify_doc(doc_id, doc_data)
        return {
            "success": True,
            "message": f"Document {doc_id} modified successfully"
        }
    except Exception as e:
        logger.error(f"Error modifying document: {e}")
        return {
            "success": False,
            "message": f"Error modifying document: {str(e)}"
        }


@mcp.tool()
async def delete_document(doc_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Delete a document.
    
    Args:
        doc_id: The ID of the document to delete
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: delete_document with doc_id: {doc_id}")
    client = get_client(ctx)
    
    try:
        await client.delete_doc(doc_id)
        return {
            "success": True,
            "message": f"Document {doc_id} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return {
            "success": False,
            "message": f"Error deleting document: {str(e)}"
        }


@mcp.tool()
async def move_document(
    doc_id: str, 
    target_workspace_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Move a document to another workspace.
    
    Args:
        doc_id: The ID of the document to move
        target_workspace_id: The ID of the target workspace
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: move_document with doc_id: {doc_id}, target_workspace_id: {target_workspace_id}")
    client = get_client(ctx)
    
    try:
        await client.move_doc(doc_id, target_workspace_id)
        return {
            "success": True,
            "message": f"Document {doc_id} moved to workspace {target_workspace_id} successfully"
        }
    except Exception as e:
        logger.error(f"Error moving document: {e}")
        return {
            "success": False,
            "message": f"Error moving document: {str(e)}"
        }


@mcp.tool()
async def list_tables(doc_id: str, ctx: Context) -> List[Dict[str, Any]]:
    """
    List all tables in a Grist document.
    
    Args:
        doc_id: The ID of the document to list tables for
        
    Returns:
        A list of tables with their IDs
    """
    logger.info(f"Tool called: list_tables with doc_id: {doc_id}")
    client = get_client(ctx)
    tables = await client.list_tables(doc_id)
    return [table.dict() for table in tables]


@mcp.tool()
async def create_table(
    doc_id: str, 
    table_id: Optional[str] = None,
    columns: Optional[List[Dict[str, Any]]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a new table in a document.
    
    Args:
        doc_id: The ID of the document to create the table in
        table_id: ID for the new table (optional, will be auto-generated if not provided)
        columns: List of column definitions (optional)
        
    Returns:
        The created table information and status
    """
    logger.info(f"Tool called: create_table with doc_id: {doc_id}")
    client = get_client(ctx)
    
    # Prepare table data
    table_data = {"tables": [{}]}
    if table_id:
        table_data["tables"][0]["id"] = table_id
    
    # Add columns if provided
    if columns:
        table_data["tables"][0]["columns"] = columns
    else:
        # Default columns if none provided
        table_data["tables"][0]["columns"] = [
            {"id": "A", "fields": {"label": "Column A"}},
            {"id": "B", "fields": {"label": "Column B"}}
        ]
    
    try:
        result = await client.create_tables(doc_id, table_data)
        return {
            "success": True,
            "message": f"Table created successfully in document {doc_id}",
            "tables": result
        }
    except Exception as e:
        logger.error(f"Error creating table: {e}")
        return {
            "success": False,
            "message": f"Error creating table: {str(e)}"
        }


@mcp.tool()
async def modify_table(
    doc_id: str, 
    table_id: str,
    fields: Dict[str, Any],
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modify a table's properties.
    
    Args:
        doc_id: The ID of the document containing the table
        table_id: The ID of the table to modify
        fields: Fields to update for the table
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: modify_table with doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    table_data = {
        "tables": [
            {
                "id": table_id,
                "fields": fields
            }
        ]
    }
    
    try:
        await client.modify_tables(doc_id, table_data)
        return {
            "success": True,
            "message": f"Table {table_id} modified successfully"
        }
    except Exception as e:
        logger.error(f"Error modifying table: {e}")
        return {
            "success": False,
            "message": f"Error modifying table: {str(e)}"
        }


@mcp.tool()
async def list_columns(doc_id: str, table_id: str, ctx: Context) -> List[Dict[str, Any]]:
    """
    List all columns in a Grist table.
    
    Args:
        doc_id: The ID of the document containing the table
        table_id: The ID of the table to list columns for
        
    Returns:
        A list of columns with their IDs and field data
    """
    logger.info(f"Tool called: list_columns with doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    columns = await client.list_columns(doc_id, table_id)
    return [column.dict() for column in columns]


@mcp.tool()
async def create_column(
    doc_id: str, 
    table_id: str,
    column_id: Optional[str] = None,
    label: Optional[str] = None,
    column_type: str = "Any",
    formula: Optional[str] = None,
    is_formula: bool = False,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a new column in a table.
    
    Args:
        doc_id: The ID of the document containing the table
        table_id: The ID of the table to add the column to
        column_id: ID for the new column (optional)
        label: Label for the column (optional)
        column_type: Type of the column (default: Any)
        formula: Formula for the column (optional)
        is_formula: Whether this is a formula column (default: False)
        
    Returns:
        The created column information and status
    """
    logger.info(f"Tool called: create_column with doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    # Prepare column data
    column_data = {"columns": [{"fields": {}}]}
    
    if column_id:
        column_data["columns"][0]["id"] = column_id
    
    fields = column_data["columns"][0]["fields"]
    if label:
        fields["label"] = label
    if column_type != "Any":
        fields["type"] = column_type
    if formula:
        fields["formula"] = formula
    if is_formula:
        fields["isFormula"] = is_formula
    
    try:
        result = await client.create_columns(doc_id, table_id, column_data)
        return {
            "success": True,
            "message": f"Column created successfully in table {table_id}",
            "columns": result
        }
    except Exception as e:
        logger.error(f"Error creating column: {e}")
        return {
            "success": False,
            "message": f"Error creating column: {str(e)}"
        }


@mcp.tool()
async def modify_column(
    doc_id: str, 
    table_id: str,
    column_id: str,
    label: Optional[str] = None,
    column_type: Optional[str] = None,
    formula: Optional[str] = None,
    is_formula: Optional[bool] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modify a column's properties.
    
    Args:
        doc_id: The ID of the document containing the table
        table_id: The ID of the table containing the column
        column_id: The ID of the column to modify
        label: New label for the column (optional)
        column_type: New type for the column (optional)
        formula: New formula for the column (optional)
        is_formula: Whether this is a formula column (optional)
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: modify_column with doc_id: {doc_id}, table_id: {table_id}, column_id: {column_id}")
    client = get_client(ctx)
    
    fields = {}
    if label is not None:
        fields["label"] = label
    if column_type is not None:
        fields["type"] = column_type
    if formula is not None:
        fields["formula"] = formula
    if is_formula is not None:
        fields["isFormula"] = is_formula
    
    if not fields:
        return {
            "success": False,
            "message": "No modification data provided"
        }
    
    column_data = {
        "columns": [
            {
                "id": column_id,
                "fields": fields
            }
        ]
    }
    
    try:
        await client.modify_columns(doc_id, table_id, column_data)
        return {
            "success": True,
            "message": f"Column {column_id} modified successfully"
        }
    except Exception as e:
        logger.error(f"Error modifying column: {e}")
        return {
            "success": False,
            "message": f"Error modifying column: {str(e)}"
        }


@mcp.tool()
async def delete_column(
    doc_id: str, 
    table_id: str,
    column_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Delete a column from a table.
    
    Args:
        doc_id: The ID of the document containing the table
        table_id: The ID of the table containing the column
        column_id: The ID of the column to delete
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: delete_column with doc_id: {doc_id}, table_id: {table_id}, column_id: {column_id}")
    client = get_client(ctx)
    
    try:
        await client.delete_column(doc_id, table_id, column_id)
        return {
            "success": True,
            "message": f"Column {column_id} deleted successfully from table {table_id}"
        }
    except Exception as e:
        logger.error(f"Error deleting column: {e}")
        return {
            "success": False,
            "message": f"Error deleting column: {str(e)}"
        }


@mcp.tool()
async def list_records(
    doc_id: str, 
    table_id: str, 
    sort: Optional[str] = None,
    limit: Optional[int] = None,
    ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    Liste les enregistrements d'une table Grist avec tri et limitation optionnels.
    
    Args:
        doc_id: L'ID du document contenant la table
        table_id: L'ID de la table à interroger
        sort: Liste optionnelle de colonnes à trier (préfixer par '-' pour ordre décroissant)
        limit: Nombre maximum optionnel d'enregistrements à retourner
        
    Returns:
        Une liste d'enregistrements avec leurs IDs et données
    """
    logger.info(f"Appel de l'outil list_records avec doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    records = await client.list_records(
        doc_id=doc_id,
        table_id=table_id,
        sort=sort,
        limit=limit
    )
    
    return [record.dict() for record in records]


@mcp.tool()
async def add_grist_records(
    doc_id: str, 
    table_id: str, 
    records: List[Dict[str, Any]], 
    ctx: Context
) -> List[int]:
    """
    Ajoute des enregistrements à une table Grist.
    
    Args:
        doc_id: L'ID du document Grist
        table_id: L'ID de la table
        records: Liste des enregistrements à ajouter. Chaque enregistrement est un dictionnaire
                où les clés sont les noms des colonnes et les valeurs sont les données.
                Exemple: [{"nom": "Dupont", "prénom": "Jean", "âge": 35}]
                
    Returns:
        Liste des IDs des enregistrements créés
    """
    logger.info(f"Tool called: add_grist_records for doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    return await client.add_records(doc_id, table_id, records)


@mcp.tool()
async def add_grist_records_safe(
    doc_id: str, 
    table_id: str, 
    records: List[Dict[str, Any]], 
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Version sécurisée d'ajout d'enregistrements avec validation préalable.
    
    Args:
        doc_id: L'ID du document Grist
        table_id: L'ID de la table
        records: Liste des enregistrements à ajouter
                
    Returns:
        Résultat détaillé avec validation et suggestions d'erreur
    """
    logger.info(f"Tool called: add_grist_records_safe for doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    try:
        # 1. Vérifier que la table existe
        table_validation = await client.validate_table_exists(doc_id, table_id)
        if not table_validation.get("exists", False):
            return {
                "success": False,
                "error": table_validation.get("error", "Table validation failed"),
                "available_tables": table_validation.get("available_tables", []),
                "suggestion": table_validation.get("suggestion"),
                "help": "Use list_tables() to see all available tables"
            }
        
        # 2. Vérifier les colonnes utilisées
        if records:
            all_column_names = set()
            for record in records:
                all_column_names.update(record.keys())
            
            column_validation = await client.validate_columns_exist(doc_id, table_id, list(all_column_names))
            if not column_validation.get("valid", False):
                return {
                    "success": False,
                    "error": "Some columns are invalid",
                    "missing_columns": column_validation.get("missing_columns", []),
                    "suggestions": column_validation.get("suggestions", {}),
                    "available_columns": column_validation.get("available_columns", []),
                    "column_labels": column_validation.get("column_labels", {}),
                    "help": "Use list_columns() to see all available columns and their IDs"
                }
        
        # 3. Si validation OK, procéder à l'insertion
        result_ids = await client.add_records(doc_id, table_id, records)
        
        return {
            "success": True,
            "message": f"Successfully added {len(result_ids)} records to table {table_id}",
            "record_ids": result_ids,
            "records_count": len(result_ids)
        }
        
    except Exception as e:
        logger.error(f"Error in add_grist_records_safe: {e}")
        return {
            "success": False,
            "error": f"Failed to add records: {str(e)}",
            "help": "Check that your data types match the column types. Use get_table_schema() for details."
        }


@mcp.tool()
async def update_grist_records(
    doc_id: str, 
    table_id: str, 
    records: List[Dict[str, Any]], 
    ctx: Context
) -> List[int]:
    """
    Met à jour des enregistrements dans une table Grist.
    
    Args:
        doc_id: L'ID du document Grist
        table_id: L'ID de la table
        records: Liste des enregistrements à mettre à jour. Chaque enregistrement doit contenir
                un champ 'id' et les champs à mettre à jour.
                Exemple: [{"id": 1, "nom": "Durand", "âge": 36}]
                
    Returns:
        Liste des IDs des enregistrements mis à jour
    """
    logger.info(f"Tool called: update_grist_records for doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    return await client.update_records(doc_id, table_id, records)


@mcp.tool()
async def delete_grist_records(
    doc_id: str, 
    table_id: str, 
    record_ids: List[int], 
    ctx: Context
) -> Dict[str, Any]:
    """
    Delete records from a Grist table.
    
    Args:
        doc_id: The ID of the Grist document
        table_id: The ID of the table
        record_ids: List of record IDs to delete
        
    Returns:
        A dictionary containing the operation status and a message
    """
    logger.info(f"Tool called: delete_grist_records for doc_id: {doc_id}, table_id: {table_id}, record_ids: {record_ids}")
    client = get_client(ctx)
    
    # Validate input data
    if not record_ids:
        return {
            "success": False,
            "message": "No record IDs provided for deletion",
            "attempted_ids": []
        }
    
    if not all(isinstance(record_id, int) for record_id in record_ids):
        return {
            "success": False,
            "message": "All record IDs must be integers",
            "attempted_ids": record_ids
        }
    
    try:
        await client.delete_records(doc_id, table_id, record_ids)
        return {
            "success": True, 
            "message": f"{len(record_ids)} records successfully deleted",
            "deleted_ids": record_ids
        }
    except Exception as e:
        logger.error(f"Error deleting records: {e}")
        return {
            "success": False,
            "message": f"Error deleting records: {str(e)}",
            "attempted_ids": record_ids
        }


@mcp.tool()
async def create_column_with_feedback(
    doc_id: str, 
    table_id: str,
    column_config: Dict[str, Any],
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Création de colonne avec retour détaillé et validation.
    
    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table
        column_config: Configuration de la colonne avec clés:
            - id: ID de la colonne (optionnel)
            - label: Label de la colonne
            - type: Type de colonne (Text, Numeric, Int, Bool, Date, etc.)
            - formula: Formule (optionnel)
            - is_formula: Si c'est une colonne de formule (défaut: False)
                
    Returns:
        Résultat détaillé avec l'état final de la colonne
    """
    logger.info(f"Tool called: create_column_with_feedback for doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    try:
        # 1. Vérifier que la table existe
        table_validation = await client.validate_table_exists(doc_id, table_id)
        if not table_validation.get("exists", False):
            return {
                "success": False,
                "error": table_validation.get("error", "Table validation failed"),
                "available_tables": table_validation.get("available_tables", []),
                "suggestion": table_validation.get("suggestion")
            }
        
        # 2. Créer la colonne
        result = await client.create_columns(
            doc_id=doc_id,
            table_id=table_id,
            columns_data={
                "columns": [{
                    **({"id": column_config["id"]} if "id" in column_config else {}),
                    "fields": {
                        **({"label": column_config["label"]} if "label" in column_config else {}),
                        **({"type": column_config["type"]} if "type" in column_config else {"type": "Text"}),
                        **({"formula": column_config["formula"]} if "formula" in column_config else {}),
                        **({"isFormula": column_config["is_formula"]} if "is_formula" in column_config else {}),
                    }
                }]
            }
        )
        
        # 3. Récupérer l'état final des colonnes pour retour détaillé
        columns = await client.list_columns(doc_id, table_id)
        
        # Trouver la colonne créée (par label ou dernière créée)
        target_label = column_config.get("label")
        created_column = None
        
        if target_label:
            created_column = next(
                (col for col in columns if col.fields.get('label') == target_label), 
                None
            )
        
        # Si pas trouvé par label, prendre la dernière des résultats
        if not created_column and result:
            created_column_id = result[0].get("id") if result else None
            if created_column_id:
                created_column = next(
                    (col for col in columns if col.id == created_column_id), 
                    None
                )
        
        return {
            "success": True,
            "message": f"Column created successfully in table {table_id}",
            "column_final_id": created_column.id if created_column else None,
            "column_config": created_column.fields if created_column else None,
            "column_label": created_column.fields.get('label') if created_column else None,
            "column_type": created_column.fields.get('type') if created_column else None,
            "all_columns_count": len(columns),
            "created_column_details": created_column.dict() if created_column else None
        }
        
    except Exception as e:
        logger.error(f"Error in create_column_with_feedback: {e}")
        return {
            "success": False,
            "error": f"Failed to create column: {str(e)}",
            "help": "Check column type validity. Use get_table_schema() to see existing columns."
        }


@mcp.tool()
async def get_formula_helpers(
    doc_id: str, 
    table_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Obtenir les références correctes pour construire des formules.
    
    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table
        
    Returns:
        Mapping complet pour construire des formules sans erreur
    """
    logger.info(f"Tool called: get_formula_helpers for doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    try:
        formula_map = await client.get_formula_column_map(doc_id, table_id)
        
        if "error" in formula_map:
            return {
                "success": False,
                "error": formula_map["error"]
            }
        
        return {
            "success": True,
            "message": f"Formula helpers for table {table_id}",
            "doc_id": doc_id,
            "table_id": table_id,
            "formula_guide": {
                "how_to_reference": "Use ${ColumnID} syntax in formulas",
                "case_sensitive": "Column IDs are case-sensitive",
                "example": "For addition: $Prix + $Taxe"
            },
            "columns": formula_map["columns"],
            "quick_reference": formula_map["formula_references"],
            "id_to_label_map": formula_map["id_to_label"]
        }
        
    except Exception as e:
        logger.error(f"Error in get_formula_helpers: {e}")
        return {
            "success": False,
            "error": f"Could not get formula helpers: {str(e)}"
        }


@mcp.tool()
async def validate_formula(
    doc_id: str, 
    table_id: str,
    formula: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Valider une formule et suggérer des corrections.
    
    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table
        formula: La formule à valider (ex: "$prix + $taxe")
        
    Returns:
        Validation avec corrections automatiques
    """
    logger.info(f"Tool called: validate_formula for doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    try:
        validation = await client.validate_formula_syntax(doc_id, table_id, formula)
        
        if "error" in validation:
            return {
                "success": False,
                "error": validation["error"]
            }
        
        result = {
            "success": True,
            "formula_valid": validation["valid"],
            "original_formula": validation["original_formula"]
        }
        
        if validation["corrected_formula"]:
            result["corrected_formula"] = validation["corrected_formula"]
            result["auto_fix_available"] = True
        
        if validation["issues"]:
            result["issues"] = validation["issues"]
            result["help"] = "Issues found in formula - see corrected_formula for fixes"
        
        if not validation["valid"]:
            result["available_columns"] = [
                f"${col['id']} (label: {col['label']})" 
                for col in validation["formula_map"]["columns"]
            ]
        
        return result
        
    except Exception as e:
        logger.error(f"Error in validate_formula: {e}")
        return {
            "success": False,
            "error": f"Could not validate formula: {str(e)}"
        }


@mcp.tool()
async def create_column_with_formula_safe(
    doc_id: str, 
    table_id: str,
    column_label: str,
    formula: str,
    column_type: str = "Any",
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Créer une colonne de formule avec validation préalable.
    
    Args:
        doc_id: L'ID du document
        table_id: L'ID de la table
        column_label: Label de la nouvelle colonne
        formula: Formule à utiliser (sera validée automatiquement)
        column_type: Type de la colonne (Any, Numeric, Text, etc.)
        
    Returns:
        Création sécurisée avec formule validée
    """
    logger.info(f"Tool called: create_column_with_formula_safe for doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    try:
        # 1. Valider la formule d'abord
        validation = await client.validate_formula_syntax(doc_id, table_id, formula)
        
        if "error" in validation:
            return {
                "success": False,
                "error": f"Formula validation failed: {validation['error']}"
            }
        
        # 2. Utiliser la formule corrigée si disponible
        final_formula = validation.get("corrected_formula", formula)
        
        if validation["issues"]:
            logger.info(f"Formula auto-corrected: {formula} -> {final_formula}")
        
        # 3. Créer la colonne avec la formule validée
        result = await client.create_columns(
            doc_id=doc_id,
            table_id=table_id,
            columns_data={
                "columns": [{
                    "fields": {
                        "label": column_label,
                        "type": column_type,
                        "formula": final_formula,
                        "isFormula": True
                    }
                }]
            }
        )
        
        # 4. Retour détaillé
        columns = await client.list_columns(doc_id, table_id)
        created_column = next(
            (col for col in columns if col.fields.get('label') == column_label), 
            None
        )
        
        response = {
            "success": True,
            "message": f"Formula column '{column_label}' created successfully",
            "column_id": created_column.id if created_column else None,
            "final_formula": final_formula
        }
        
        if validation["issues"]:
            response["formula_corrections"] = {
                "original": formula,
                "corrected": final_formula,
                "issues_fixed": validation["issues"]
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in create_column_with_formula_safe: {e}")
        return {
            "success": False,
            "error": f"Could not create formula column: {str(e)}"
        }


@mcp.tool()
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
    Cette fonction est optimisée pour les cas d'utilisation courants de filtrage.
    
    Args:
        doc_id: ID du document
        table_id: ID de la table à filtrer
        columns: Liste des colonnes à sélectionner (toutes par défaut)
        where_conditions: Conditions de filtrage sous forme de dictionnaire
                         Exemple: {"organisation": "OPSIA", "status": "actif"}
        order_by: Colonne pour le tri (optionnel)
        limit: Nombre maximum de résultats (optionnel)
        ctx: Contexte MCP
        
    Returns:
        Résultats de la requête de filtrage
    """
    client = get_client(ctx)
    
    # Construction de la requête SQL
    columns_str = "*" if not columns else ", ".join(columns)
    sql_query = f"SELECT {columns_str} FROM {table_id}"
    
    # Ajout des conditions WHERE
    if where_conditions:
        conditions = []
        for column, value in where_conditions.items():
            if isinstance(value, str):
                conditions.append(f"{column} = '{value}'")
            else:
                conditions.append(f"{column} = {value}")
        sql_query += " WHERE " + " AND ".join(conditions)
    
    # Ajout du tri
    if order_by:
        sql_query += f" ORDER BY {order_by}"
    
    # Ajout de la limite
    if limit:
        sql_query += f" LIMIT {limit}"
    
    # Exécution de la requête
    result = await client._request(
        "POST",
        f"/docs/{doc_id}/sql",
        json_data={"sql": sql_query}
    )
    
    return {
        "success": True,
        "message": "Requête de filtrage exécutée avec succès",
        "doc_id": doc_id,
        "table_id": table_id,
        "query": sql_query,
        "record_count": len(result.get("records", [])),
        "records": result.get("records", [])
    }


@mcp.tool()
async def execute_sql_query(
    doc_id: str,
    sql_query: str,
    parameters: Optional[List[Any]] = None,
    timeout_ms: Optional[int] = 1000,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Exécute une requête SQL générale sur un document Grist.
    Cette fonction est destinée aux requêtes SQL complexes et personnalisées.
    
    Args:
        doc_id: ID du document
        sql_query: Requête SQL à exécuter (SELECT uniquement)
        parameters: Paramètres pour la requête SQL (optionnel)
        timeout_ms: Délai d'expiration en millisecondes (1000 par défaut)
        ctx: Contexte MCP
        
    Returns:
        Résultats de la requête SQL
    """
    client = get_client(ctx)
    
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
        "message": "Requête SQL exécutée avec succès",
        "doc_id": doc_id,
        "query": sql_query,
        "record_count": len(result.get("records", [])),
        "records": result.get("records", [])
    }


# Access Management Tools
@mcp.tool()
async def list_organization_access(org_id: Union[int, str], ctx: Context) -> Dict[str, Any]:
    """
    List users with access to an organization.
    
    Args:
        org_id: The ID of the organization
        
    Returns:
        List of users with their access levels
    """
    logger.info(f"Tool called: list_organization_access with org_id: {org_id}")
    client = get_client(ctx)
    return await client.list_org_access(org_id)


@mcp.tool()
async def modify_organization_access(
    org_id: Union[int, str], 
    user_email: str,
    access_level: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modify user access to an organization.
    
    Args:
        org_id: The ID of the organization
        user_email: Email of the user to modify access for
        access_level: Access level (owners, editors, viewers, members, or null to remove)
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: modify_organization_access with org_id: {org_id}, user_email: {user_email}")
    client = get_client(ctx)
    
    if access_level not in ["owners", "editors", "viewers", "members", "null"]:
        return {
            "success": False,
            "message": "Invalid access level. Must be: owners, editors, viewers, members, or null"
        }
    
    access_delta = {
        "users": {
            user_email: None if access_level == "null" else access_level
        }
    }
    
    try:
        await client.modify_org_access(org_id, access_delta)
        action = "removed" if access_level == "null" else f"set to {access_level}"
        return {
            "success": True,
            "message": f"Access for {user_email} {action} successfully"
        }
    except Exception as e:
        logger.error(f"Error modifying organization access: {e}")
        return {
            "success": False,
            "message": f"Error modifying access: {str(e)}"
        }


@mcp.tool()
async def list_workspace_access(workspace_id: int, ctx: Context) -> Dict[str, Any]:
    """
    List users with access to a workspace.
    
    Args:
        workspace_id: The ID of the workspace
        
    Returns:
        List of users with their access levels
    """
    logger.info(f"Tool called: list_workspace_access with workspace_id: {workspace_id}")
    client = get_client(ctx)
    return await client.list_workspace_access(workspace_id)


@mcp.tool()
async def modify_workspace_access(
    workspace_id: int, 
    user_email: str,
    access_level: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modify user access to a workspace.
    
    Args:
        workspace_id: The ID of the workspace
        user_email: Email of the user to modify access for
        access_level: Access level (owners, editors, viewers, members, or null to remove)
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: modify_workspace_access with workspace_id: {workspace_id}, user_email: {user_email}")
    client = get_client(ctx)
    
    if access_level not in ["owners", "editors", "viewers", "members", "null"]:
        return {
            "success": False,
            "message": "Invalid access level. Must be: owners, editors, viewers, members, or null"
        }
    
    access_delta = {
        "users": {
            user_email: None if access_level == "null" else access_level
        }
    }
    
    try:
        await client.modify_workspace_access(workspace_id, access_delta)
        action = "removed" if access_level == "null" else f"set to {access_level}"
        return {
            "success": True,
            "message": f"Access for {user_email} {action} successfully"
        }
    except Exception as e:
        logger.error(f"Error modifying workspace access: {e}")
        return {
            "success": False,
            "message": f"Error modifying access: {str(e)}"
        }


@mcp.tool()
async def list_document_access(doc_id: str, ctx: Context) -> Dict[str, Any]:
    """
    List users with access to a document.
    
    Args:
        doc_id: The ID of the document
        
    Returns:
        List of users with their access levels
    """
    logger.info(f"Tool called: list_document_access with doc_id: {doc_id}")
    client = get_client(ctx)
    return await client.list_doc_access(doc_id)


@mcp.tool()
async def modify_document_access(
    doc_id: str, 
    user_email: str,
    access_level: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modify user access to a document.
    
    Args:
        doc_id: The ID of the document
        user_email: Email of the user to modify access for
        access_level: Access level (owners, editors, viewers, members, or null to remove)
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: modify_document_access with doc_id: {doc_id}, user_email: {user_email}")
    client = get_client(ctx)
    
    if access_level not in ["owners", "editors", "viewers", "members", "null"]:
        return {
            "success": False,
            "message": "Invalid access level. Must be: owners, editors, viewers, members, or null"
        }
    
    access_delta = {
        "users": {
            user_email: None if access_level == "null" else access_level
        }
    }
    
    try:
        await client.modify_doc_access(doc_id, access_delta)
        action = "removed" if access_level == "null" else f"set to {access_level}"
        return {
            "success": True,
            "message": f"Access for {user_email} {action} successfully"
        }
    except Exception as e:
        logger.error(f"Error modifying document access: {e}")
        return {
            "success": False,
            "message": f"Error modifying access: {str(e)}"
        }


# Download and Export Tools
@mcp.tool()
async def download_document_sqlite(
    doc_id: str, 
    remove_history: bool = False,
    as_template: bool = False,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Download a document as SQLite file.
    
    Args:
        doc_id: The ID of the document to download
        remove_history: Remove document history to reduce file size
        as_template: Remove all data and history but keep structure
        
    Returns:
        Information about the download operation
    """
    logger.info(f"Tool called: download_document_sqlite with doc_id: {doc_id}")
    client = get_client(ctx)
    
    try:
        content = await client.download_doc(doc_id, nohistory=remove_history, template=as_template)
        return {
            "success": True,
            "message": f"Document {doc_id} downloaded successfully as SQLite",
            "file_size": len(content),
            "format": "application/x-sqlite3",
            "content_base64": content.hex()  # Return as hex for JSON serialization
        }
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        return {
            "success": False,
            "message": f"Error downloading document: {str(e)}"
        }


@mcp.tool()
async def download_document_excel(
    doc_id: str, 
    header_format: str = "label",
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Download a document as Excel file.
    
    Args:
        doc_id: The ID of the document to download
        header_format: Header format (label or colId)
        
    Returns:
        Information about the download operation
    """
    logger.info(f"Tool called: download_document_excel with doc_id: {doc_id}")
    client = get_client(ctx)
    
    if header_format not in ["label", "colId"]:
        return {
            "success": False,
            "message": "Invalid header format. Must be 'label' or 'colId'"
        }
    
    try:
        content = await client.download_doc_xlsx(doc_id, header=header_format)
        return {
            "success": True,
            "message": f"Document {doc_id} downloaded successfully as Excel",
            "file_size": len(content),
            "format": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "content_base64": content.hex()  # Return as hex for JSON serialization
        }
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        return {
            "success": False,
            "message": f"Error downloading document: {str(e)}"
        }


@mcp.tool()
async def download_table_csv(
    doc_id: str, 
    table_id: str,
    header_format: str = "label",
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Download a table as CSV file.
    
    Args:
        doc_id: The ID of the document containing the table
        table_id: The ID of the table to download
        header_format: Header format (label or colId)
        
    Returns:
        CSV content and information
    """
    logger.info(f"Tool called: download_table_csv with doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    if header_format not in ["label", "colId"]:
        return {
            "success": False,
            "message": "Invalid header format. Must be 'label' or 'colId'"
        }
    
    try:
        csv_content = await client.download_doc_csv(doc_id, table_id, header=header_format)
        return {
            "success": True,
            "message": f"Table {table_id} downloaded successfully as CSV",
            "table_id": table_id,
            "format": "text/csv",
            "content": csv_content,
            "size": len(csv_content)
        }
    except Exception as e:
        logger.error(f"Error downloading table: {e}")
        return {
            "success": False,
            "message": f"Error downloading table: {str(e)}"
        }


@mcp.tool()
async def get_table_schema(
    doc_id: str, 
    table_id: str,
    header_format: str = "label",
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get the schema of a table following frictionlessdata table-schema standard.
    
    Args:
        doc_id: The ID of the document containing the table
        table_id: The ID of the table
        header_format: Header format (label or colId)
        
    Returns:
        Table schema information
    """
    logger.info(f"Tool called: get_table_schema with doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    if header_format not in ["label", "colId"]:
        return {
            "success": False,
            "message": "Invalid header format. Must be 'label' or 'colId'"
        }
    
    try:
        schema = await client.download_table_schema(doc_id, table_id, header=header_format)
        return {
            "success": True,
            "message": f"Schema for table {table_id} retrieved successfully",
            "table_id": table_id,
            "schema": schema
        }
    except Exception as e:
        logger.error(f"Error getting table schema: {e}")
        return {
            "success": False,
            "message": f"Error getting table schema: {str(e)}"
        }


@mcp.tool()
async def force_reload_document(doc_id: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Force reload a document (closes and reopens it, restarting the Python engine).
    
    Args:
        doc_id: The ID of the document to reload
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: force_reload_document with doc_id: {doc_id}")
    client = get_client(ctx)
    
    try:
        await client.force_reload_doc(doc_id)
        return {
            "success": True,
            "message": f"Document {doc_id} reloaded successfully"
        }
    except Exception as e:
        logger.error(f"Error reloading document: {e}")
        return {
            "success": False,
            "message": f"Error reloading document: {str(e)}"
        }


@mcp.tool()
async def delete_document_history(
    doc_id: str, 
    keep_actions: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Truncate the document's action history, keeping only the latest actions.
    
    Args:
        doc_id: The ID of the document
        keep_actions: Number of the latest history actions to keep
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: delete_document_history with doc_id: {doc_id}, keep_actions: {keep_actions}")
    client = get_client(ctx)
    
    if keep_actions < 0:
        return {
            "success": False,
            "message": "keep_actions must be a non-negative integer"
        }
    
    try:
        await client.delete_doc_history(doc_id, keep_actions)
        return {
            "success": True,
            "message": f"Document history truncated, keeping {keep_actions} latest actions"
        }
    except Exception as e:
        logger.error(f"Error deleting document history: {e}")
        return {
            "success": False,
            "message": f"Error deleting document history: {str(e)}"
        }


# Attachment Management Tools
@mcp.tool()
async def list_attachments(
    doc_id: str, 
    sort: Optional[str] = None,
    limit: Optional[int] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    List all attachments in a document.
    
    Args:
        doc_id: The ID of the document
        sort: Sort order (optional)
        limit: Maximum number of attachments to return (optional)
        
    Returns:
        List of attachments with their metadata
    """
    logger.info(f"Tool called: list_attachments with doc_id: {doc_id}")
    client = get_client(ctx)
    
    try:
        attachments = await client.list_attachments(doc_id, sort=sort, limit=limit)
        return {
            "success": True,
            "message": f"Found {len(attachments)} attachments in document {doc_id}",
            "doc_id": doc_id,
            "count": len(attachments),
            "attachments": attachments
        }
    except Exception as e:
        logger.error(f"Error listing attachments: {e}")
        return {
            "success": False,
            "message": f"Error listing attachments: {str(e)}"
        }


@mcp.tool()
async def get_attachment_info(
    doc_id: str, 
    attachment_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get metadata for a specific attachment.
    
    Args:
        doc_id: The ID of the document
        attachment_id: The ID of the attachment
        
    Returns:
        Attachment metadata
    """
    logger.info(f"Tool called: get_attachment_info with doc_id: {doc_id}, attachment_id: {attachment_id}")
    client = get_client(ctx)
    
    try:
        metadata = await client.get_attachment_metadata(doc_id, attachment_id)
        return {
            "success": True,
            "message": f"Retrieved metadata for attachment {attachment_id}",
            "doc_id": doc_id,
            "attachment_id": attachment_id,
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Error getting attachment metadata: {e}")
        return {
            "success": False,
            "message": f"Error getting attachment metadata: {str(e)}"
        }


@mcp.tool()
async def download_attachment(
    doc_id: str, 
    attachment_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Download the contents of an attachment.
    
    Args:
        doc_id: The ID of the document
        attachment_id: The ID of the attachment to download
        
    Returns:
        Attachment content (encoded as base64 for JSON serialization)
    """
    logger.info(f"Tool called: download_attachment with doc_id: {doc_id}, attachment_id: {attachment_id}")
    client = get_client(ctx)
    
    try:
        content = await client.download_attachment(doc_id, attachment_id)
        return {
            "success": True,
            "message": f"Downloaded attachment {attachment_id} successfully",
            "doc_id": doc_id,
            "attachment_id": attachment_id,
            "file_size": len(content),
            "content_base64": content.hex()  # Return as hex for JSON serialization
        }
    except Exception as e:
        logger.error(f"Error downloading attachment: {e}")
        return {
            "success": False,
            "message": f"Error downloading attachment: {str(e)}"
        }


@mcp.tool()
async def upload_attachment(
    doc_id: str, 
    filename: str,
    content_base64: str,
    content_type: str = "application/octet-stream",
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Upload an attachment to a document.
    
    Args:
        doc_id: The ID of the document
        filename: Name of the file to upload
        content_base64: File content encoded as base64
        content_type: MIME type of the file (default: application/octet-stream)
        
    Returns:
        Upload result with attachment ID
    """
    logger.info(f"Tool called: upload_attachment with doc_id: {doc_id}, filename: {filename}")
    client = get_client(ctx)
    
    try:
        # Decode base64 content
        import base64
        content = base64.b64decode(content_base64)
        
        # Upload the file
        files = [(filename, content, content_type)]
        result = await client.upload_attachments(doc_id, files)
        
        return {
            "success": True,
            "message": f"File '{filename}' uploaded successfully",
            "doc_id": doc_id,
            "filename": filename,
            "file_size": len(content),
            "content_type": content_type,
            "attachment_ids": result
        }
    except Exception as e:
        logger.error(f"Error uploading attachment: {e}")
        return {
            "success": False,
            "message": f"Error uploading attachment: {str(e)}"
        }


# Webhook Management Tools
@mcp.tool()
async def list_webhooks(doc_id: str, ctx: Context = None) -> Dict[str, Any]:
    """
    List all webhooks associated with a document.
    
    Args:
        doc_id: The ID of the document
        
    Returns:
        List of webhooks with their configurations
    """
    logger.info(f"Tool called: list_webhooks with doc_id: {doc_id}")
    client = get_client(ctx)
    
    try:
        webhooks = await client.list_webhooks(doc_id)
        return {
            "success": True,
            "message": f"Found {len(webhooks)} webhooks for document {doc_id}",
            "doc_id": doc_id,
            "count": len(webhooks),
            "webhooks": webhooks
        }
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        return {
            "success": False,
            "message": f"Error listing webhooks: {str(e)}"
        }


@mcp.tool()
async def create_webhook(
    doc_id: str,
    name: str,
    url: str,
    table_id: str,
    event_types: List[str],
    memo: Optional[str] = None,
    enabled: bool = True,
    is_ready_column: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a new webhook for a document.
    
    Args:
        doc_id: The ID of the document
        name: Name for the webhook
        url: URL to send webhook requests to
        table_id: ID of the table to monitor
        event_types: List of event types (add, update, etc.)
        memo: Optional description
        enabled: Whether the webhook is enabled (default: True)
        is_ready_column: Optional column to check if record is ready
        
    Returns:
        Created webhook information
    """
    logger.info(f"Tool called: create_webhook with doc_id: {doc_id}, name: {name}")
    client = get_client(ctx)
    
    webhook_config = {
        "name": name,
        "url": url,
        "tableId": table_id,
        "eventTypes": event_types,
        "enabled": enabled
    }
    
    if memo:
        webhook_config["memo"] = memo
    if is_ready_column:
        webhook_config["isReadyColumn"] = is_ready_column
    
    try:
        result = await client.create_webhooks(doc_id, [webhook_config])
        return {
            "success": True,
            "message": f"Webhook '{name}' created successfully",
            "doc_id": doc_id,
            "webhook": result[0] if result else None
        }
    except Exception as e:
        logger.error(f"Error creating webhook: {e}")
        return {
            "success": False,
            "message": f"Error creating webhook: {str(e)}"
        }


@mcp.tool()
async def modify_webhook(
    doc_id: str,
    webhook_id: str,
    name: Optional[str] = None,
    url: Optional[str] = None,
    enabled: Optional[bool] = None,
    memo: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    is_ready_column: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Modify an existing webhook.
    
    Args:
        doc_id: The ID of the document
        webhook_id: The ID of the webhook to modify
        name: New name (optional)
        url: New URL (optional)
        enabled: New enabled status (optional)
        memo: New memo (optional)
        event_types: New event types (optional)
        is_ready_column: New ready column (optional)
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: modify_webhook with doc_id: {doc_id}, webhook_id: {webhook_id}")
    client = get_client(ctx)
    
    webhook_data = {}
    if name is not None:
        webhook_data["name"] = name
    if url is not None:
        webhook_data["url"] = url
    if enabled is not None:
        webhook_data["enabled"] = enabled
    if memo is not None:
        webhook_data["memo"] = memo
    if event_types is not None:
        webhook_data["eventTypes"] = event_types
    if is_ready_column is not None:
        webhook_data["isReadyColumn"] = is_ready_column
    
    if not webhook_data:
        return {
            "success": False,
            "message": "No modification data provided"
        }
    
    try:
        await client.modify_webhook(doc_id, webhook_id, webhook_data)
        return {
            "success": True,
            "message": f"Webhook {webhook_id} modified successfully"
        }
    except Exception as e:
        logger.error(f"Error modifying webhook: {e}")
        return {
            "success": False,
            "message": f"Error modifying webhook: {str(e)}"
        }


@mcp.tool()
async def delete_webhook(
    doc_id: str,
    webhook_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Delete a webhook.
    
    Args:
        doc_id: The ID of the document
        webhook_id: The ID of the webhook to delete
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: delete_webhook with doc_id: {doc_id}, webhook_id: {webhook_id}")
    client = get_client(ctx)
    
    try:
        result = await client.delete_webhook(doc_id, webhook_id)
        return {
            "success": True,
            "message": f"Webhook {webhook_id} deleted successfully",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        return {
            "success": False,
            "message": f"Error deleting webhook: {str(e)}"
        }


@mcp.tool()
async def clear_webhook_queue(doc_id: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Clear the queue of undelivered webhook payloads for a document.
    
    Args:
        doc_id: The ID of the document
        
    Returns:
        Status of the operation
    """
    logger.info(f"Tool called: clear_webhook_queue with doc_id: {doc_id}")
    client = get_client(ctx)
    
    try:
        await client.clear_webhook_queue(doc_id)
        return {
            "success": True,
            "message": f"Webhook queue cleared for document {doc_id}"
        }
    except Exception as e:
        logger.error(f"Error clearing webhook queue: {e}")
        return {
            "success": False,
            "message": f"Error clearing webhook queue: {str(e)}"
        }


def main():
    """
    Point d'entrée principal du serveur MCP Grist.
    Supporte les transports : stdio (défaut), streamable-http, et sse.
    """
    import argparse
    from typing import Literal
    
    parser = argparse.ArgumentParser(description="Grist MCP Server")
    parser.add_argument(
        "--transport", 
        type=str,
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="Type de transport à utiliser (stdio, streamable-http, ou sse)"
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Hôte pour les transports HTTP")
    parser.add_argument("--port", type=int, default=8000, help="Port pour les transports HTTP")
    parser.add_argument("--path", type=str, default="/mcp", help="Chemin pour streamable-http")
    parser.add_argument("--mount-path", type=str, default="/sse", help="Chemin pour SSE")
    parser.add_argument("--debug", action="store_true", help="Active le mode debug")
    
    args = parser.parse_args()
    
    # Configuration du logging en mode debug si demandé
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode debug activé")
    
    # Vérifier si la clé API est configurée
    api_key = os.environ.get("GRIST_API_KEY")
    if not api_key:
        logger.critical("GRIST_API_KEY n'est pas définie. Veuillez configurer cette variable d'environnement.")
        print("Erreur: La clé API Grist n'est pas configurée. Définissez GRIST_API_KEY dans l'environnement ou le fichier .env")
        sys.exit(1)
    
    logger.info(f"Démarrage du serveur MCP Grist v{__version__} avec transport: {args.transport}")
    
    try:
        if args.transport == "stdio":
            mcp.run(transport="stdio")
        elif args.transport == "streamable-http":
            mcp.run(
                transport="streamable-http", 
                host=args.host, 
                port=args.port,
                path=args.path
            )
        elif args.transport == "sse":
            mcp.run(
                transport="sse", 
                host=args.host, 
                port=args.port,
                mount_path=args.mount_path
            )
    except Exception as e:
        logger.critical(f"Erreur lors du démarrage du serveur: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
