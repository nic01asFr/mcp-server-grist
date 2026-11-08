# Grist MCP Server

[![PyPI version](https://img.shields.io/pypi/v/mcp-server-grist.svg)](https://pypi.org/project/mcp-server-grist/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-server-grist.svg)](https://pypi.org/project/mcp-server-grist/)
[![Tests](https://img.shields.io/github/actions/workflow/status/nic01asFr/mcp-server-grist/tests.yml?branch=official&label=tests)](https://github.com/nic01asFr/mcp-server-grist/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*[Version française](https://github.com/nic01asFr/mcp-server-grist/blob/official/README.fr.md)*

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server for the [Grist](https://www.getgrist.com) API. It lets AI assistants such as Claude read and edit your Grist data: browse documents, query tables with SQL, add and update records, and create tables, columns and whole schemas with relations between tables.

Works with any Grist instance: [docs.getgrist.com](https://docs.getgrist.com), self-hosted Grist, or [grist.numerique.gouv.fr](https://grist.numerique.gouv.fr).

## Quick start

You need Python 3.10+ and a Grist API key (Grist: *Profile settings → API*).

Add the server to your MCP client configuration. For Claude Desktop, edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "grist": {
      "command": "uvx",
      "args": ["mcp-server-grist"],
      "env": {
        "GRIST_API_KEY": "your_grist_api_key",
        "GRIST_API_URL": "https://docs.getgrist.com/api"
      }
    }
  }
}
```

[`uvx`](https://docs.astral.sh/uv/) downloads and runs the package, no installation needed. Restart your client: the Grist tools are now available to the assistant.

## Configuration

| Variable | Required | Description |
|---|---|---|
| `GRIST_API_KEY` | yes | Your Grist API key |
| `GRIST_API_URL` | no | API URL of your Grist instance, e.g. `https://docs.getgrist.com/api` (default) or `https://grist.example.org/api` |
| `GRIST_API_HOST` | no | Older name for the same setting, used when `GRIST_API_URL` is not set |
| `LOG_LEVEL` | no | `DEBUG`, `INFO` (default), `WARNING`, `ERROR` |

Variables can also be set in a `.env` file (see `.env.template`).

## Other ways to run the server

### With pip

```bash
pip install mcp-server-grist
mcp-server-grist                    # stdio, for local MCP clients
```

In your MCP client, use `"command": "mcp-server-grist"` (or `"command": "python", "args": ["-m", "mcp_server_grist"]`) with the same `env` block as above.

### Over HTTP

```bash
mcp-server-grist --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

| Option | Default | Description |
|---|---|---|
| `--transport` | `stdio` | `stdio`, `streamable-http`, or `sse` (deprecated) |
| `--host` | `127.0.0.1` | Interface for HTTP transports |
| `--port` | `8000` | Port for HTTP transports |
| `--path` | `/mcp` | Endpoint for `streamable-http` |
| `--mount-path` | `/sse` | Endpoint for `sse` |
| `--debug` | | Verbose logging |

**Security:** the server does not authenticate HTTP clients. Anyone who can reach it acts with your Grist API key. Keep the default `127.0.0.1`, and put a reverse proxy with HTTPS and authentication in front of it before exposing it to a network.

### With Docker

```bash
docker build -t mcp/grist-mcp-server .

# stdio
docker run -i --rm -e GRIST_API_KEY=your_key -e GRIST_API_URL=https://docs.getgrist.com/api \
  mcp/grist-mcp-server

# HTTP (--host 0.0.0.0 is required inside a container)
docker run --rm -p 8000:8000 -e GRIST_API_KEY=your_key \
  mcp/grist-mcp-server --transport streamable-http --host 0.0.0.0
```

Without `GRIST_API_URL`, the image uses `https://grist.numerique.gouv.fr/api`. In an MCP client, use `"command": "docker"` with `"args": ["run", "-i", "--rm", "-e", "GRIST_API_KEY=...", "mcp/grist-mcp-server"]`.

`docker compose up` starts a stdio and an HTTP service, configured from `.env`.

## Available tools

The server exposes 54 tools. The [tools reference](https://github.com/nic01asFr/mcp-server-grist/blob/official/docs/tools-reference.mdx) lists the parameters of each one.

### Navigation
- `list_organizations`: list organizations
- `describe_organization`: details of an organization
- `list_workspaces`: list the workspaces of an organization
- `describe_workspace`: details of a workspace
- `list_documents`: list the documents of a workspace
- `describe_document`: details of a document
- `list_tables`: list the tables of a document
- `list_columns`: list the columns of a table
- `list_records`: list records, with sorting and limit
- `get_table_schema`: detailed schema of a table

### Records
- `add_grist_records`: add records
- `add_grist_records_safe`: add records after checking the column names
- `update_grist_records`: update records
- `delete_grist_records`: delete records

### SQL queries
- `filter_sql_query`: filter a table without writing SQL (conditions, sorting, limit)
- `execute_sql_query`: run a custom `SELECT` query (joins, subqueries, parameters, timeout)

### Administration
- `modify_organization`, `delete_organization`: manage an organization
- `create_workspace`, `modify_workspace`, `delete_workspace`: manage workspaces
- `create_document`, `modify_document`, `delete_document`: manage documents
- `move_document`: move a document to another workspace
- `force_reload_document`: reload a document
- `delete_document_history`: trim a document's history
- `create_table`, `modify_table`: create or rename a table
- `create_column`, `modify_column`, `delete_column`: manage columns (types, formulas, choices, references)

### Schemas and relations
- `create_schema`: create tables, their columns, the relations between them and initial data in one call
- `validate_schema`: check a schema without creating anything
- `create_reference_column`: create a reference column showing the chosen column of the target table, optionally with a two-way (reverse) relation
- `export_schema`: export a document's schema as JSON, YAML or a Mermaid diagram

### Access management
- `list_organization_access`, `modify_organization_access`: users of an organization
- `list_workspace_access`, `modify_workspace_access`: users of a workspace
- `list_document_access`, `modify_document_access`: users of a document

### Export
- `download_document_sqlite`: download a document as SQLite
- `download_document_excel`: download a table as Excel
- `download_table_csv`: download a table as CSV

### Attachments
- `list_attachments`: list the attachments of a document
- `get_attachment_info`: metadata of an attachment
- `download_attachment`: download an attachment
- `upload_attachment`: upload an attachment

### Webhooks
- `list_webhooks`, `create_webhook`, `modify_webhook`, `delete_webhook`: manage webhooks
- `clear_webhook_queue`: empty the webhook queue

## Examples

You normally just ask the assistant in plain language ("create a Projects table linked to Tasks"); it chooses the tools. The examples below show the corresponding tool calls and their arguments.

```python
# Explore
await list_tables(doc_id="abc123")
await list_records(doc_id="abc123", table_id="Tasks", sort="-due_date", limit=10)

# Filter without SQL
await filter_sql_query(
    doc_id="abc123",
    table_id="Tasks",
    columns=["title", "status"],
    where_conditions={"status": "open"},
    order_by="title",
    limit=20
)

# Custom SQL (SELECT only)
await execute_sql_query(
    doc_id="abc123",
    sql_query="SELECT t.title, p.name FROM Tasks t JOIN Projects p ON t.project = p.id WHERE t.status = ?",
    parameters=["open"]
)

# Add and update records
await add_grist_records(doc_id="abc123", table_id="Tasks",
                        records=[{"title": "Write docs", "status": "open"}])
await update_grist_records(doc_id="abc123", table_id="Tasks",
                           records=[{"id": 1, "status": "done"}])

# Formula column
await create_column(doc_id="abc123", table_id="Orders", column_id="total",
                    column_type="Numeric", label="Total", formula="$price * $quantity")

# Two related tables in one call
await create_schema(
    doc_id="abc123",
    schema={
        "tables": {
            "Projects": {"columns": {"name": {"type": "Text", "label": "Name"}}},
            "Tasks": {"columns": {
                "title": "Text",
                "status": {"type": "Choice", "choices": ["open", "done"]},
                "project": {"type": "Ref", "target": "Projects",
                            "visible": "name", "reverse": "tasks"}
            }}
        },
        "data": {"Projects": [{"name": "Website"}]}
    }
)

# Export a table to Excel
await download_document_excel(doc_id="abc123", table_id="Tasks", header="label")

# Share a document
await modify_document_access(doc_id="abc123", user_email="someone@example.com",
                             access_level="editors")
```

In a schema, a reference column is written `{"type": "Ref", "target": "Table", "visible": "column"}` (or `"Ref:Table"`). `"visible"` is the column displayed in the cell; `"reverse"` adds the matching column in the target table, kept in sync by Grist. Re-running the same schema creates nothing twice: existing tables are left untouched.

## Development

```bash
git clone https://github.com/nic01asFr/mcp-server-grist.git
cd mcp-server-grist
pip install -e ".[dev]"
pytest tests/
```

The tools reference is generated from the code: after changing a tool, run `python scripts/generate_tools_reference.py`. See [CONTRIBUTING.md](https://github.com/nic01asFr/mcp-server-grist/blob/official/CONTRIBUTING.md) for the contribution and release process, and the [CHANGELOG](https://github.com/nic01asFr/mcp-server-grist/blob/official/CHANGELOG.md) for version history.

## License

MIT
