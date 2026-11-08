# Grist MCP Server

[![PyPI version](https://img.shields.io/pypi/v/mcp-server-grist.svg)](https://pypi.org/project/mcp-server-grist/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-server-grist.svg)](https://pypi.org/project/mcp-server-grist/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*[English version](https://github.com/nic01asFr/mcp-server-grist/blob/official/README.md)*

Un serveur [MCP](https://modelcontextprotocol.io) (Model Context Protocol) pour l'API [Grist](https://www.getgrist.com). Il permet aux assistants IA comme Claude de lire et de modifier vos données Grist : parcourir les documents, interroger les tables en SQL, ajouter et modifier des enregistrements, créer des tables, des colonnes et des schémas complets avec des relations entre tables.

Fonctionne avec toute instance Grist : [docs.getgrist.com](https://docs.getgrist.com), Grist auto-hébergé ou [grist.numerique.gouv.fr](https://grist.numerique.gouv.fr).

## Démarrage rapide

Il faut Python 3.10+ et une clé API Grist (dans Grist : *Paramètres du profil → API*).

Ajoutez le serveur à la configuration de votre client MCP. Pour Claude Desktop, modifiez `claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "grist": {
      "command": "uvx",
      "args": ["mcp-server-grist"],
      "env": {
        "GRIST_API_KEY": "votre_clé_api_grist",
        "GRIST_API_URL": "https://docs.getgrist.com/api"
      }
    }
  }
}
```

[`uvx`](https://docs.astral.sh/uv/) télécharge et lance le paquet, sans installation préalable. Redémarrez votre client : les outils Grist sont alors disponibles pour l'assistant.

## Configuration

| Variable | Obligatoire | Description |
|---|---|---|
| `GRIST_API_KEY` | oui | Votre clé API Grist |
| `GRIST_API_URL` | non | URL de l'API de votre instance, ex. `https://docs.getgrist.com/api` (défaut) ou `https://grist.example.org/api` |
| `GRIST_API_HOST` | non | Ancien nom du même réglage, utilisé si `GRIST_API_URL` n'est pas défini |
| `LOG_LEVEL` | non | `DEBUG`, `INFO` (défaut), `WARNING`, `ERROR` |

Ces variables peuvent aussi être placées dans un fichier `.env` (voir `.env.template`).

## Autres façons de lancer le serveur

### Avec pip

```bash
pip install mcp-server-grist
mcp-server-grist                    # stdio, pour les clients MCP locaux
```

Dans votre client MCP, utilisez `"command": "mcp-server-grist"` (ou `"command": "python", "args": ["-m", "mcp_server_grist"]`) avec le même bloc `env` que ci-dessus.

### En HTTP

```bash
mcp-server-grist --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

| Option | Défaut | Description |
|---|---|---|
| `--transport` | `stdio` | `stdio`, `streamable-http` ou `sse` (déprécié) |
| `--host` | `127.0.0.1` | Interface pour les transports HTTP |
| `--port` | `8000` | Port pour les transports HTTP |
| `--path` | `/mcp` | Point d'accès pour `streamable-http` |
| `--mount-path` | `/sse` | Point d'accès pour `sse` |
| `--debug` | | Journalisation détaillée |

**Sécurité :** le serveur n'authentifie pas ses clients HTTP. Quiconque l'atteint agit avec votre clé API Grist. Gardez `127.0.0.1` (valeur par défaut), et placez un proxy inverse avec HTTPS et authentification devant le serveur avant de l'exposer sur un réseau.

### Avec Docker

```bash
docker build -t mcp/grist-mcp-server .

# stdio
docker run -i --rm -e GRIST_API_KEY=votre_clé -e GRIST_API_URL=https://docs.getgrist.com/api \
  mcp/grist-mcp-server

# HTTP (--host 0.0.0.0 est nécessaire dans un conteneur)
docker run --rm -p 8000:8000 -e GRIST_API_KEY=votre_clé \
  mcp/grist-mcp-server --transport streamable-http --host 0.0.0.0
```

Sans `GRIST_API_URL`, l'image utilise `https://grist.numerique.gouv.fr/api`. Dans un client MCP, utilisez `"command": "docker"` avec `"args": ["run", "-i", "--rm", "-e", "GRIST_API_KEY=...", "mcp/grist-mcp-server"]`.

`docker compose up` lance un service stdio et un service HTTP, configurés par le fichier `.env`.

## Outils disponibles

Le serveur expose 54 outils. La [référence des outils](https://github.com/nic01asFr/mcp-server-grist/blob/official/docs/tools-reference.mdx) détaille les paramètres de chacun.

### Navigation
- `list_organizations` : liste les organisations
- `describe_organization` : détails d'une organisation
- `list_workspaces` : liste les espaces de travail d'une organisation
- `describe_workspace` : détails d'un espace de travail
- `list_documents` : liste les documents d'un espace de travail
- `describe_document` : détails d'un document
- `list_tables` : liste les tables d'un document
- `list_columns` : liste les colonnes d'une table
- `list_records` : liste les enregistrements, avec tri et limite
- `get_table_schema` : schéma détaillé d'une table

### Enregistrements
- `add_grist_records` : ajoute des enregistrements
- `add_grist_records_safe` : ajoute des enregistrements après vérification des noms de colonnes
- `update_grist_records` : met à jour des enregistrements
- `delete_grist_records` : supprime des enregistrements

### Requêtes SQL
- `filter_sql_query` : filtre une table sans écrire de SQL (conditions, tri, limite)
- `execute_sql_query` : exécute une requête `SELECT` personnalisée (jointures, sous-requêtes, paramètres, timeout)

### Administration
- `modify_organization`, `delete_organization` : gèrent une organisation
- `create_workspace`, `modify_workspace`, `delete_workspace` : gèrent les espaces de travail
- `create_document`, `modify_document`, `delete_document` : gèrent les documents
- `move_document` : déplace un document vers un autre espace de travail
- `force_reload_document` : recharge un document
- `delete_document_history` : réduit l'historique d'un document
- `create_table`, `modify_table` : créent ou renomment une table
- `create_column`, `modify_column`, `delete_column` : gèrent les colonnes (types, formules, choix, références)

### Schémas et relations
- `create_schema` : crée en un appel des tables, leurs colonnes, les relations entre elles et des données initiales
- `validate_schema` : vérifie un schéma sans rien créer
- `create_reference_column` : crée une colonne référence qui affiche la colonne choisie de la table cible, avec en option une relation à double sens (inverse)
- `export_schema` : exporte le schéma d'un document en JSON, YAML ou diagramme Mermaid

### Gestion des accès
- `list_organization_access`, `modify_organization_access` : utilisateurs d'une organisation
- `list_workspace_access`, `modify_workspace_access` : utilisateurs d'un espace de travail
- `list_document_access`, `modify_document_access` : utilisateurs d'un document

### Export
- `download_document_sqlite` : télécharge un document au format SQLite
- `download_document_excel` : télécharge une table au format Excel
- `download_table_csv` : télécharge une table au format CSV

### Pièces jointes
- `list_attachments` : liste les pièces jointes d'un document
- `get_attachment_info` : métadonnées d'une pièce jointe
- `download_attachment` : télécharge une pièce jointe
- `upload_attachment` : téléverse une pièce jointe

### Webhooks
- `list_webhooks`, `create_webhook`, `modify_webhook`, `delete_webhook` : gèrent les webhooks
- `clear_webhook_queue` : vide la file d'attente des webhooks

## Exemples

En pratique, vous demandez simplement à l'assistant en langage courant (« crée une table Projets reliée aux Tâches ») ; il choisit les outils. Les exemples ci-dessous montrent les appels d'outils correspondants et leurs arguments.

```python
# Explorer
await list_tables(doc_id="abc123")
await list_records(doc_id="abc123", table_id="Taches", sort="-echeance", limit=10)

# Filtrer sans SQL
await filter_sql_query(
    doc_id="abc123",
    table_id="Taches",
    columns=["titre", "statut"],
    where_conditions={"statut": "ouvert"},
    order_by="titre",
    limit=20
)

# SQL personnalisé (SELECT uniquement)
await execute_sql_query(
    doc_id="abc123",
    sql_query="SELECT t.titre, p.nom FROM Taches t JOIN Projets p ON t.projet = p.id WHERE t.statut = ?",
    parameters=["ouvert"]
)

# Ajouter et modifier des enregistrements
await add_grist_records(doc_id="abc123", table_id="Taches",
                        records=[{"titre": "Rédiger la doc", "statut": "ouvert"}])
await update_grist_records(doc_id="abc123", table_id="Taches",
                           records=[{"id": 1, "statut": "fait"}])

# Colonne calculée
await create_column(doc_id="abc123", table_id="Commandes", column_id="total",
                    column_type="Numeric", label="Total", formula="$prix * $quantite")

# Deux tables reliées en un appel
await create_schema(
    doc_id="abc123",
    schema={
        "tables": {
            "Projets": {"columns": {"nom": {"type": "Text", "label": "Nom"}}},
            "Taches": {"columns": {
                "titre": "Text",
                "statut": {"type": "Choice", "choices": ["ouvert", "fait"]},
                "projet": {"type": "Ref", "target": "Projets",
                           "visible": "nom", "reverse": "taches"}
            }}
        },
        "data": {"Projets": [{"nom": "Site web"}]}
    }
)

# Exporter une table en Excel
await download_document_excel(doc_id="abc123", table_id="Taches", header="label")

# Partager un document
await modify_document_access(doc_id="abc123", user_email="quelquun@exemple.fr",
                             access_level="editors")
```

Dans un schéma, une colonne référence s'écrit `{"type": "Ref", "target": "Table", "visible": "colonne"}` (ou `"Ref:Table"`). `"visible"` est la colonne affichée dans la cellule ; `"reverse"` ajoute la colonne correspondante dans la table cible, synchronisée par Grist. Relancer le même schéma ne crée rien en double : les tables existantes ne sont pas modifiées.

## Développement

```bash
git clone https://github.com/nic01asFr/mcp-server-grist.git
cd mcp-server-grist
pip install -e ".[dev]"
pytest tests/
```

La référence des outils est générée depuis le code : après avoir modifié un outil, lancez `python scripts/generate_tools_reference.py`. Voir [CONTRIBUTING.md](https://github.com/nic01asFr/mcp-server-grist/blob/official/CONTRIBUTING.md) pour la contribution et la publication, et le [CHANGELOG](https://github.com/nic01asFr/mcp-server-grist/blob/official/CHANGELOG.md) pour l'historique des versions.

## Licence

MIT
