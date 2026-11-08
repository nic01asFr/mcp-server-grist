"""
Tests du point d'entrée et des transports (code actuel : mcp_server_grist.main).

Remplace l'ancienne version qui testait le module obsolète `grist_mcp_server`.
"""
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# Le package réexporte la fonction main() sous le même nom : on importe le module.
main_module = importlib.import_module("mcp_server_grist.main")


def run_main(argv):
    """Lance main() avec les arguments donnés et un serveur MCP factice."""
    server = MagicMock()
    with patch.object(sys, "argv", ["mcp-server-grist", *argv]), \
         patch.object(main_module, "create_mcp_server", return_value=server):
        code = main_module.main()
    return code, server


def test_defaults_to_stdio_on_localhost():
    with patch.object(sys, "argv", ["mcp-server-grist"]):
        args = main_module.parse_args()
    assert (args.transport, args.host, args.port, args.path) == ("stdio", "127.0.0.1", 8000, "/mcp")


def test_unknown_transport_rejected():
    with patch.object(sys, "argv", ["mcp-server-grist", "--transport", "websocket"]):
        with pytest.raises(SystemExit):
            main_module.parse_args()


def test_stdio_runs_server_synchronously():
    # FastMCP.run() est synchrone : main() doit l'appeler directement
    # (l'envelopper dans asyncio.run faisait planter l'arrêt du serveur).
    code, server = run_main([])
    assert code == 0
    server.run.assert_called_once_with()


def test_streamable_http_arguments():
    code, server = run_main(["--transport", "streamable-http", "--host", "0.0.0.0",
                             "--port", "9000", "--path", "/api/mcp"])
    assert code == 0
    server.run.assert_called_once_with(transport="streamable-http", host="0.0.0.0",
                                       port=9000, path="/api/mcp")


def test_sse_passes_mount_path_as_path():
    code, server = run_main(["--transport", "sse", "--mount-path", "/events"])
    assert code == 0
    server.run.assert_called_once_with(transport="sse", host="127.0.0.1", port=8000, path="/events")


def test_server_error_returns_nonzero():
    server = MagicMock()
    server.run.side_effect = RuntimeError("boom")
    with patch.object(sys, "argv", ["mcp-server-grist"]), \
         patch.object(main_module, "create_mcp_server", return_value=server):
        assert main_module.main() == 1
