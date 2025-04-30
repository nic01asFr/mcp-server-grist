# Documentation du Serveur MCP Grist

Bienvenue dans la documentation officielle du serveur MCP Grist. Ce serveur permet d'interagir avec l'API Grist directement depuis des modèles de langage comme Claude.

## Installation

```bash
pip install mcp-server-grist
```

## Configuration rapide

1. Créez un fichier `.env` avec vos identifiants Grist :
```env
GRIST_API_KEY=votre_clé_api
GRIST_API_HOST=https://docs.getgrist.com/api
```

2. Configurez Claude Desktop :
```json
{
  "mcpServers": {
    "grist-mcp": {
      "command": "python",
      "args": ["-m", "grist_mcp_server"]
    }
  }
}
```

## Fonctionnalités principales

- Accès aux données Grist
- Gestion des organisations et documents
- Manipulation des tables et enregistrements
- Requêtes SQL (SELECT)
- Authentification sécurisée

## Exemples d'utilisation

Consultez notre [README](../README.md) pour des exemples détaillés d'utilisation.

## Support

Pour toute question ou problème :
- Ouvrez une issue sur [GitHub](https://github.com/modelcontextprotocol/server-grist/issues)
- Consultez la [documentation complète](../README.md)

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](../LICENSE) pour plus de détails. 