#!/usr/bin/env python3
"""
Test script for the Grist MCP Server
"""

import os
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if the required environment variables are set
def check_env_vars():
    """Check if the required environment variables are set"""
    required_vars = ["GRIST_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in a .env file or in your environment.")
        return False
    
    return True

# Test the Grist API connection
async def test_api_connection():
    """Test the connection to the Grist API"""
    from grist_mcp_server import get_client
    
    try:
        client = get_client()
        print(f"Successfully created Grist client with URL: {client.api_url}")
        
        # Test listing organizations
        orgs = await client.list_orgs()
        print(f"Found {len(orgs)} organizations")
        
        if orgs:
            org = orgs[0]
            print(f"Testing with organization: {org.name} (ID: {org.id})")
            
            # Test listing workspaces
            workspaces = await client.list_workspaces(org.id)
            print(f"Found {len(workspaces)} workspaces in organization {org.id}")
            
            if workspaces:
                workspace = workspaces[0]
                print(f"Testing with workspace: {workspace.name} (ID: {workspace.id})")
                
                # Test listing documents
                documents = await client.list_documents(workspace.id)
                print(f"Found {len(documents)} documents in workspace {workspace.id}")
                
                if documents:
                    document = documents[0]
                    print(f"Testing with document: {document.name} (ID: {document.id})")
                    
                    # Test listing tables
                    tables = await client.list_tables(document.id)
                    print(f"Found {len(tables)} tables in document {document.id}")
                    
                    if tables:
                        table = tables[0]
                        print(f"Testing with table: {table.id}")
                        
                        # Test listing columns
                        columns = await client.list_columns(document.id, table.id)
                        print(f"Found {len(columns)} columns in table {table.id}")
                        
                        # Test listing records
                        records = await client.list_records(document.id, table.id, limit=5)
                        print(f"Found {len(records)} records in table {table.id} (limited to 5)")
                        
                        if records:
                            print("API connection test completed successfully!")
                            return True
        
        print("Could not complete all API tests due to insufficient data.")
        return False
        
    except Exception as e:
        print(f"ERROR connecting to Grist API: {e}")
        return False

async def main():
    """Main function"""
    print("Testing Grist MCP Server...")
    
    if not check_env_vars():
        return
    
    if await test_api_connection():
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed.")

if __name__ == "__main__":
    asyncio.run(main())