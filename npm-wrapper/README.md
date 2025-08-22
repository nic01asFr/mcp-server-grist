# Serveur MCP pour Grist

Ce package fournit un serveur MCP (Model Context Protocol) pour l'API Grist, permettant aux modèles d'IA comme Claude d'interagir avec vos données Grist.

## Prérequis

- Node.js 14+
- Python 3.8+
- Le package Python `mcp-server-grist` installé

## Installation

```bash
npm install -g @modelcontextprotocol/server-grist
```

## Utilisation avec Claude Desktop

Dans votre fichier de configuration `mcp_servers.json` :

```json
{
  "servers": [
    {
      "id": "grist",
      "name": "Grist MCP Server",
      "description": "Serveur MCP pour l'API Grist",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-grist"
      ],
      "env": {
        "GRIST_API_KEY": "votre_clé_api_grist",
        "GRIST_API_URL": "https://docs.getgrist.com/api"
      }
    }
  ]
}
```

## Variables d'environnement

- `GRIST_API_KEY` (obligatoire) : Votre clé API Grist
- `GRIST_API_URL` (optionnel) : URL de l'API Grist, par défaut "https://docs.getgrist.com/api"

## Fonctionnalités

Ce serveur MCP expose 50 outils pour interagir avec l'API Grist, notamment :

- Navigation (lister les organisations, espaces de travail, documents, tables, etc.)
- Gestion des enregistrements (ajouter, modifier, supprimer)
- Requêtes SQL
- Administration (créer, modifier, supprimer des ressources)
- Gestion des pièces jointes
- Gestion des webhooks

## Licence

MIT
