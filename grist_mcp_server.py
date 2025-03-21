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
    from mcp.server.fastmcp import FastMCP, Context
except ImportError:
    print("Error: fastmcp package not found. Please install it with: pip install fastmcp")
    sys.exit(1)

# Version
__version__ = "0.1.0"

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
    instructions="""
    Use this server to interact with the Grist API. 
    You can list organizations, workspaces, documents, tables, columns, and records. 
    You can also add, update, and delete records.
    
    Typical workflow:
    1. List organizations with list_organizations
    2. Get workspaces for an organization with list_workspaces
    3. Get documents in a workspace with list_documents
    4. Get tables in a document with list_tables
    5. Get columns in a table with list_columns
    6. Get, add, update or delete records with the corresponding tools
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
                        filter_data: Optional[Dict[str, List[Any]]] = None, 
                        sort: Optional[str] = None,
                        limit: Optional[int] = None) -> List[GristRecord]:
        """List records in a table with optional filtering, sorting, and limiting"""
        params = {}
        if filter_data:
            params["filter"] = json.dumps(filter_data)
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
        """Delete records from a table by their IDs
        
        Args:
            doc_id: Grist document ID
            table_id: Table ID
            record_ids: List of record IDs to delete
        """
        if not record_ids:
            logger.warning("No record IDs provided for deletion")
            return
            
        logger.debug(f"Deleting {len(record_ids)} records from table {table_id} in document {doc_id}")
        
        try:
            # First method: use data/delete endpoint with ID list
            await self._request(
                "POST",
                f"/docs/{doc_id}/tables/{table_id}/data/delete",
                json_data=record_ids
            )
            logger.info(f"{len(record_ids)} records successfully deleted (method 1)")
            return
        except Exception as e:
            logger.warning(f"First deletion method failed: {e}")
            
            try:
                # Second method: use records endpoint with DELETE method
                formatted_records = {
                    "records": [{"id": record_id} for record_id in record_ids]
                }
                
                await self._request(
                    "DELETE",
                    f"/docs/{doc_id}/tables/{table_id}/records",
                    json_data=formatted_records
                )
                logger.info(f"{len(record_ids)} records successfully deleted (method 2)")
                return
            except Exception as e2:
                logger.warning(f"Second deletion method failed: {e2}")
                
                try:
                    # Third method: use empty fields and PATCH endpoint
                    formatted_records = {
                        "records": [{"id": record_id, "fields": {}} for record_id in record_ids]
                    }
                    
                    await self._request(
                        "PATCH",
                        f"/docs/{doc_id}/tables/{table_id}/records",
                        json_data=formatted_records
                    )
                    logger.info(f"{len(record_ids)} records updated with empty fields (method 3)")
                    return
                except Exception as e3:
                    logger.error(f"All deletion methods failed: {e3}")
                    raise ValueError(f"Could not delete records. Errors: {e}, {e2}, {e3}")


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
async def list_records(
    doc_id: str, 
    table_id: str, 
    filter_json: Optional[str] = None,
    sort: Optional[str] = None,
    limit: Optional[int] = None,
    ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    List records in a Grist table with optional filtering, sorting, and limiting.
    
    Args:
        doc_id: The ID of the document containing the table
        table_id: The ID of the table to list records from
        filter_json: Optional JSON string for filtering records (e.g., '{"column_name": ["value1", "value2"]}')
        sort: Optional comma-separated list of columns to sort by (prefix with '-' for descending order)
        limit: Optional maximum number of records to return
        
    Returns:
        A list of records with their IDs and field data
    """
    logger.info(f"Tool called: list_records with doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
    filter_data = None
    if filter_json:
        try:
            filter_data = json.loads(filter_json)
            logger.debug(f"Parsed filter_json: {filter_data}")
        except json.JSONDecodeError as e:
            error_msg = f"Invalid filter JSON: {filter_json}"
            logger.error(f"{error_msg}: {e}")
            raise ValueError(error_msg)
    
    records = await client.list_records(
        doc_id=doc_id,
        table_id=table_id,
        filter_data=filter_data,
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
    Supprime des enregistrements d'une table Grist.
    
    Args:
        doc_id: L'ID du document Grist
        table_id: L'ID de la table
        record_ids: Liste des IDs des enregistrements à supprimer
        
    Returns:
        Un dictionnaire contenant le statut de l'opération et un message
    """
    logger.info(f"Tool called: delete_grist_records for doc_id: {doc_id}, table_id: {table_id}")
    client = get_client(ctx)
    
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


def main():
    """Run the MCP server"""
    logger.info(f"Starting Grist MCP Server v{__version__}")

    # Importation et initialisation de l'outil de commandes de Noël
    try:
        import christmas_order_tool
        # Initialisation des outils avec le mcp et la fonction get_client
        christmas_tools = christmas_order_tool.init_christmas_tools(mcp, get_client)
        logger.info("Module de commandes de Noël chargé avec succès")
    except ImportError as e:
        logger.error(f"Erreur lors de l'importation du module de commandes de Noël: {e}")
    
    # Log environment variables with sensitive info masked
    env_vars = {
        "GRIST_API_KEY": mask_api_key(os.environ.get("GRIST_API_KEY", "")),
        "GRIST_API_URL": os.environ.get("GRIST_API_URL", ""),
        "GRIST_API_HOST": os.environ.get("GRIST_API_HOST", ""),
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO")
    }
    logger.info(f"Environment configuration: {env_vars}")
    
    # Test connection to Grist API
    try:
        client = get_client()
        logger.info(f"Successfully initialized Grist client with URL: {client.api_url}")
    except Exception as e:
        logger.error(f"Failed to initialize Grist client: {e}")
    
    mcp.run()


if __name__ == "__main__":
    main()
