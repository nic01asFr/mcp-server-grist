"""
Tests de sécurité du serveur MCP Grist (code actuel : package mcp_server_grist).

Remplace l'ancienne version qui testait le module obsolète `grist_mcp_server`.
"""
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_grist.client import get_client, mask_api_key
from mcp_server_grist.tools import queries


def test_mask_api_key_hides_the_middle():
    masked = mask_api_key("abcdef1234567890xyz")
    assert masked == "abcde...90xyz"
    assert "12345678" not in masked


def test_mask_api_key_short_key_fully_hidden():
    assert mask_api_key("short") == "[SET]"


def test_client_requires_api_key(monkeypatch):
    monkeypatch.setenv("GRIST_API_KEY", "")
    with patch("mcp_server_grist.client.load_dotenv"):
        with pytest.raises(ValueError):
            get_client()


@pytest.mark.parametrize("order_by", [
    "nom; DROP TABLE x",
    "nom DESC, (SELECT 1)",
    'nom" --',
    "1=1",
])
async def test_filter_sql_query_rejects_order_by_injection(order_by):
    with patch.object(queries, "execute_sql_query", new=AsyncMock()) as execute:
        result = await queries.filter_sql_query("doc", "Table1", order_by=order_by)
    assert result["success"] is False
    execute.assert_not_called()


async def test_filter_sql_query_quotes_order_by_and_parameterizes_values():
    with patch.object(queries, "execute_sql_query", new=AsyncMock(return_value={"success": True})) as execute:
        await queries.filter_sql_query(
            "doc", "Table1", where_conditions={"statut": "x' OR '1'='1"}, order_by="nom desc")
    kwargs = execute.call_args.kwargs
    assert kwargs["sql_query"] == 'SELECT * FROM "Table1" WHERE "statut" = ? ORDER BY "nom" DESC'
    assert kwargs["parameters"] == ["x' OR '1'='1"]


async def test_execute_sql_query_only_allows_select():
    for sql in ("DELETE FROM Table1", "UPDATE Table1 SET a=1", "DROP TABLE Table1"):
        result = await queries.execute_sql_query("doc", sql)
        assert result["success"] is False
