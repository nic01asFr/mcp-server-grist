"""
MCP Server Grist - Serveur Model Context Protocol pour l'API Grist.

Ce package fournit un serveur MCP qui expose les fonctionnalités
de l'API Grist aux modèles de langage via le protocole MCP.
"""

from .version import __version__
from .main import main

__all__ = ["__version__", "main"]