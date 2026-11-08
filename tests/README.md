# Tests MCP Server Grist

Tests automatisés du serveur MCP Grist. Ils n'appellent aucune instance Grist :
le client Grist est simulé.

## Fichiers

- `test_client.py` : client HTTP `GristClient`
- `test_navigation_tools.py`, `test_records_tools.py`, `test_access_tools.py` : outils MCP
- `test_schema.py` : types et préparation des requêtes de schéma
- `test_schema_tools.py` : outils de schéma et de colonnes (`create_schema`,
  `create_reference_column`, `create_table`, `create_column`…), avec un faux
  client qui reproduit le comportement réel de Grist
- `test_transport.py` : point d'entrée et transports (stdio, streamable-http, sse)
- `test_security.py` : masquage de la clé API, protection contre l'injection SQL
- `test_compliance.py` : conformité au protocole MCP
- `test_docs.py` : la documentation correspond aux outils réels (référence générée à
  jour, README sans outil ni paramètre inexistant)

## Exécution

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Intégration continue

Les tests sont exécutés par GitHub Actions sur chaque pull request et chaque push
vers `official`. La publication sur PyPI ne part que si les tests passent.
