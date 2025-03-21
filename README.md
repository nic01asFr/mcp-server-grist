# Grist MCP Server

An MCP server implementation that provides tools for interacting with the Grist API, enabling integration between Grist spreadsheets and language models.

## Features

- Access Grist data directly from language models
- List organizations, workspaces, documents, tables, and columns
- Query, add, update, and delete records in Grist tables
- Filter and sort data with rich query capabilities
- Secure API key-based authentication

## Tools

### list_organizations
List all Grist organizations that the user has access to.

**Returns:** A list of organizations with their IDs, names, and domains.

### list_workspaces
List all workspaces in a Grist organization.

**Inputs:**
- `org_id` (int or string): The ID of the organization to list workspaces for

**Returns:** A list of workspaces with their IDs and names.

### list_documents
List all documents in a Grist workspace.

**Inputs:**
- `workspace_id` (int): The ID of the workspace to list documents for

**Returns:** A list of documents with their IDs and names.

### list_tables
List all tables in a Grist document.

**Inputs:**
- `doc_id` (string): The ID of the document to list tables for

**Returns:** A list of tables with their IDs.

### list_columns
List all columns in a Grist table.

**Inputs:**
- `doc_id` (string): The ID of the document containing the table
- `table_id` (string): The ID of the table to list columns for

**Returns:** A list of columns with their IDs and field data.

### list_records
List records in a Grist table with optional filtering, sorting, and limiting.

**Inputs:**
- `doc_id` (string): The ID of the document containing the table
- `table_id` (string): The ID of the table to list records from
- `filter_json` (string, optional): JSON string for filtering records (e.g., '{"column_name": ["value1", "value2"]}')
- `sort` (string, optional): Comma-separated list of columns to sort by (prefix with '-' for descending order)
- `limit` (int, optional): Maximum number of records to return

**Returns:** A list of records with their IDs and field data.

### add_grist_records
Add records to a Grist table.

**Inputs:**
- `doc_id` (string): The ID of the document containing the table
- `table_id` (string): The ID of the table to add records to
- `records` (array): List of records to add as dictionaries of field values

**Returns:** A list of IDs for the newly created records.

### update_grist_records
Update records in a Grist table.

**Inputs:**
- `doc_id` (string): The ID of the document containing the table
- `table_id` (string): The ID of the table to update records in
- `records` (array): List of records to update (each must include "id" and field values)

**Returns:** A list of IDs for the updated records.

### delete_grist_records
Delete records from a Grist table.

**Inputs:**
- `doc_id` (string): The ID of the document containing the table
- `table_id` (string): The ID of the table to delete records from
- `record_ids` (array): List of record IDs to delete

**Returns:** A dictionary containing the operation status and a message.

## Usage

The Grist MCP Server is designed for:
- Analyzing and summarizing Grist data
- Creating, updating, and deleting records programmatically
- Building reports and visualizations based on Grist data
- Answering questions about data stored in Grist tables
- Connecting Grist with language models for natural language queries

## Requirements

- Python 3.8+
- A valid Grist API key
- The following Python packages: `fastmcp`, `httpx`, `pydantic`, `python-dotenv`

## Setup

### Environment Variables

Create a `.env` file with the following:

```
GRIST_API_KEY=your_api_key_here
GRIST_API_HOST=https://docs.getgrist.com/api
```

Replace `your_api_key_here` with your actual Grist API key, which you can find in your Grist account settings.

## Configuration

### Usage with Claude Desktop

Add this to your `claude_desktop_config.json`:

#### Direct Python

```json
{
  "mcpServers": {
    "grist-mcp": {
      "command": "python",
      "args": [
        "-m", "grist_mcp_server"
      ]
    }
  }
}
```

#### Docker

```json
{
  "mcpServers": {
    "grist-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e", "GRIST_API_KEY=your_api_key_here",
        "-e", "GRIST_API_HOST=https://docs.getgrist.com/api",
        "mcp/grist-mcp-server"
      ]
    }
  }
}
```

## Building

Docker:

```bash
docker build -t mcp/grist-mcp-server .
```

## Installation

```bash
pip install mcp-server-grist
```

Or manually:

```bash
git clone https://github.com/yourusername/mcp-server-grist.git
cd mcp-server-grist
pip install -r requirements.txt
```

## License

This MCP server is licensed under the MIT License.