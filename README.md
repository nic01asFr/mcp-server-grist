# Grist MCP Server

[![PyPI version](https://img.shields.io/pypi/v/mcp-server-grist.svg)](https://pypi.org/project/mcp-server-grist/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-server-grist.svg)](https://pypi.org/project/mcp-server-grist/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Un serveur MCP (Model Context Protocol) pour interagir avec l'API Grist. Ce serveur permet d'accéder et de manipuler les données Grist directement depuis des modèles de langage comme Claude.

## Structure du projet

```
mcp-server-grist/
├── src/
│   └── mcp_server_grist/     # Package principal
│       ├── __init__.py       # Point d'entrée du package
│       ├── __main__.py       # Support pour exécution en module
│       ├── version.py        # Gestion de version
│       ├── main.py           # Point d'entrée principal
│       ├── server.py         # Configuration du serveur MCP
│       ├── client.py         # Client API Grist
│       ├── tools/            # Outils MCP organisés par catégorie
│       └── models.py         # Modèles de données Pydantic
├── tests/                    # Tests unitaires et d'intégration
├── docs/                     # Documentation détaillée
├── requirements.txt          # Dépendances Python
├── pyproject.toml           # Configuration moderne du package
├── Dockerfile               # Configuration Docker
├── docker-compose.yml       # Configuration multi-services
├── .env.template            # Template pour variables d'environnement
└── README.md                # Documentation principale
```

## Prérequis

- Python 3.8+
- Une clé API Grist valide
- Les packages Python suivants : `fastmcp`, `httpx`, `pydantic`, `python-dotenv`

## Installation

### Via pip (recommandé)

```bash
pip install mcp-server-grist
```

Après l'installation, vous pouvez exécuter le serveur avec :

```bash
mcp-server-grist
```

### Utilisation avec Claude Desktop

Pour utiliser ce serveur MCP avec Claude Desktop, ajoutez la configuration suivante à votre fichier `mcp_servers.json` :

```json
{
  "mcpServers": {
    "grist-mcp": {
      "command": "node",
      "args": [
        "chemin/vers/npm-wrapper/bin/start.js"
      ],
      "env": {
        "GRIST_API_KEY": "votre_clé_api_grist",
        "GRIST_API_URL": "https://docs.getgrist.com/api"
      }
    }
  }
}
```

Remplacez `chemin/vers/npm-wrapper/bin/start.js` par le chemin absolu vers le script `start.js` du wrapper Node.js inclus dans ce package.

### Installation en mode développement

Pour contribuer ou personnaliser le serveur :

```bash
# Cloner le repository
git clone https://github.com/modelcontextprotocol/mcp-server-grist.git
cd mcp-server-grist

# Installer en mode développement
pip install -e .

# Lancer les tests
python -m pytest tests
```

### Via Docker

Pour un déploiement rapide avec Docker :

```bash
# Construire l'image
docker build -t mcp/grist-mcp-server .

# Exécuter le container
docker run -it --rm \
  -e GRIST_API_KEY=votre_clé_api \
  -e GRIST_API_HOST=https://docs.getgrist.com/api \
  mcp/grist-mcp-server
```

### Via Docker Compose

Pour déployer plusieurs modes de transport en parallèle :

```bash
# Configurer les variables d'environnement
cp .env.example .env
# Éditer le fichier .env avec votre clé API

# Lancer les services
docker-compose up
```

## Configuration

### Variables d'environnement

Créez un fichier `.env` basé sur `.env.template` avec les variables suivantes :
```
GRIST_API_KEY=votre_clé_api
GRIST_API_HOST=https://docs.getgrist.com/api
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

Vous trouverez votre clé API dans les paramètres de votre compte Grist.

### Configuration avec Claude Desktop

Ajoutez ceci à votre `claude_desktop_config.json` :

#### Version Python

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

#### Version Docker

```json
{
  "mcpServers": {
    "grist-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e", "GRIST_API_KEY=votre_clé_api",
        "-e", "GRIST_API_HOST=https://docs.getgrist.com/api",
        "mcp/grist-mcp-server"
      ]
    }
  }
}
```

## Options de démarrage

Le serveur prend en charge plusieurs modes de transport conformes au standard MCP :

### En mode module (recommandé)

```bash
# Mode stdio (par défaut pour Claude)
python -m mcp_server_grist --transport stdio

# Mode HTTP streamable (pour intégration web)
python -m mcp_server_grist --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp

# Mode Server-Sent Events (déprécié selon MCP 2025-03-26)
python -m mcp_server_grist --transport sse --host 127.0.0.1 --port 8000 --mount-path /sse

# Active le mode debug avec logging détaillé
python -m mcp_server_grist --debug
```

### Options supplémentaires

```
Options:
  --transport {stdio,streamable-http,sse}
                        Type de transport à utiliser
  --host HOST           Hôte pour les transports HTTP (défaut: 127.0.0.1)
  --port PORT           Port pour les transports HTTP (défaut: 8000)
  --path PATH           Chemin pour streamable-http (défaut: /mcp)
  --mount-path MOUNT_PATH
                        Chemin pour SSE (défaut: /sse)
  --debug               Active le mode debug
  --help                Affiche l'aide
```

### Sécurité des transports

Pour les transports HTTP et SSE, nous recommandons :

- Utiliser `127.0.0.1` (localhost) plutôt que `0.0.0.0` pour limiter l'accès au réseau local
- Activer la validation d'origine (`validate_origin`) pour éviter les attaques DNS rebinding
- Pour une exposition à Internet, utiliser un proxy inverse avec HTTPS

## Fonctionnalités

- Accès aux données Grist directement depuis les modèles de langage
- Liste des organisations, espaces de travail, documents, tables et colonnes
- Gestion des enregistrements (création, lecture, mise à jour, suppression)
- Filtrage et tri des données avec des capacités de requêtage avancées
- Support des requêtes SQL (SELECT uniquement)
- Authentification sécurisée via clé API
- Gestion des accès utilisateurs
- Export et téléchargement (SQLite, Excel, CSV)
- Gestion des pièces jointes
- Gestion des webhooks
- Validation intelligente des formules

## Outils disponibles

### Gestion des organisations et documents
- `list_organizations` : Liste les organisations
- `describe_organization` : Obtient des informations détaillées sur une organisation
- `modify_organization` : Modifie une organisation
- `delete_organization` : Supprime une organisation
- `list_workspaces` : Liste les espaces de travail dans une organisation
- `describe_workspace` : Obtient des informations détaillées sur un espace de travail
- `create_workspace` : Crée un nouvel espace de travail
- `modify_workspace` : Modifie un espace de travail
- `delete_workspace` : Supprime un espace de travail
- `list_documents` : Liste les documents dans un espace de travail
- `describe_document` : Obtient des informations détaillées sur un document
- `create_document` : Crée un nouveau document
- `modify_document` : Modifie un document
- `delete_document` : Supprime un document
- `move_document` : Déplace un document vers un autre espace de travail
- `force_reload_document` : Force le rechargement d'un document
- `delete_document_history` : Supprime l'historique d'un document

### Gestion des tables et colonnes
- `list_tables` : Liste les tables dans un document
- `create_table` : Crée une nouvelle table
- `modify_table` : Modifie une table
- `list_columns` : Liste les colonnes dans une table
- `create_column` : Crée une nouvelle colonne
- `create_column_with_feedback` : Crée une colonne avec validation et retour détaillé
- `modify_column` : Modifie une colonne
- `delete_column` : Supprime une colonne
- `create_column_with_formula_safe` : Crée une colonne de formule avec validation
- `get_formula_helpers` : Obtient de l'aide pour construire des formules
- `validate_formula` : Valide une formule et suggère des corrections
- `get_table_schema` : Obtient le schéma d'une table

### Manipulation des données
- `list_records` : Liste les enregistrements avec tri et limite
- `add_grist_records` : Ajoute des enregistrements
- `add_grist_records_safe` : Ajoute des enregistrements avec validation
- `update_grist_records` : Met à jour des enregistrements
- `delete_grist_records` : Supprime des enregistrements

### Filtrage et requêtes SQL
- `filter_sql_query` : Requête SQL optimisée pour le filtrage simple
  * Interface simplifiée pour les filtres courants
  * Support du tri et de la limitation
  * Conditions WHERE basiques
- `execute_sql_query` : Requête SQL complexe
  * Requêtes SQL personnalisées
  * Support des JOIN et sous-requêtes
  * Paramètres et timeout configurables

### Gestion des accès
- `list_organization_access` : Liste les utilisateurs ayant accès à une organisation
- `modify_organization_access` : Modifie l'accès d'un utilisateur à une organisation
- `list_workspace_access` : Liste les utilisateurs ayant accès à un espace de travail
- `modify_workspace_access` : Modifie l'accès d'un utilisateur à un espace de travail
- `list_document_access` : Liste les utilisateurs ayant accès à un document
- `modify_document_access` : Modifie l'accès d'un utilisateur à un document

### Export et téléchargement
- `download_document_sqlite` : Télécharge un document au format SQLite
- `download_document_excel` : Télécharge un document au format Excel
- `download_table_csv` : Télécharge une table au format CSV

### Gestion des pièces jointes
- `list_attachments` : Liste les pièces jointes dans un document
- `get_attachment_info` : Obtient des informations sur une pièce jointe
- `download_attachment` : Télécharge une pièce jointe
- `upload_attachment` : Téléverse une pièce jointe

### Gestion des webhooks
- `list_webhooks` : Liste les webhooks d'un document
- `create_webhook` : Crée un webhook
- `modify_webhook` : Modifie un webhook
- `delete_webhook` : Supprime un webhook
- `clear_webhook_queue` : Vide la file d'attente des webhooks

## Exemples d'utilisation

```python
# Liste des organisations
orgs = await list_organizations()

# Liste des espaces de travail
workspaces = await list_workspaces(org_id=1)

# Liste des documents
docs = await list_documents(workspace_id=1)

# Liste des tables
tables = await list_tables(doc_id="abc123")

# Liste des colonnes
columns = await list_columns(doc_id="abc123", table_id="Table1")

# Liste des enregistrements avec tri et limite
records = await list_records(
    doc_id="abc123",
    table_id="Table1",
    sort="name",
    limit=10
)

# Filtrage simple avec filter_sql_query
filtered_records = await filter_sql_query(
    doc_id="abc123",
    table_id="Table1",
    columns=["name", "age", "status"],
    where_conditions={
        "organisation": "OPSIA",
        "status": "actif"
    },
    order_by="name",
    limit=10
)

# Requête SQL complexe avec execute_sql_query
sql_result = await execute_sql_query(
    doc_id="abc123",
    sql_query="""
        SELECT t1.name, t1.age, t2.department
        FROM Table1 t1
        JOIN Table2 t2 ON t1.id = t2.employee_id
        WHERE t1.status = ? AND t1.age > ?
        ORDER BY t1.name
        LIMIT ?
    """,
    parameters=["actif", 25, 10],
    timeout_ms=2000
)

# Ajout d'enregistrements
new_records = await add_grist_records(
    doc_id="abc123",
    table_id="Table1",
    records=[{"name": "John", "age": 30}]
)

# Mise à jour d'enregistrements
updated_records = await update_grist_records(
    doc_id="abc123",
    table_id="Table1",
    records=[{"id": 1, "name": "John", "age": 31}]
)

# Création d'une colonne de formule avec validation
formula_column = await create_column_with_formula_safe(
    doc_id="abc123",
    table_id="Table1",
    column_label="Total",
    formula="$Prix * $Quantité",
    column_type="Numeric"
)

# Téléchargement d'un document au format Excel
excel_doc = await download_document_excel(
    doc_id="abc123",
    header_format="label"
)

# Gestion des accès
await modify_document_access(
    doc_id="abc123",
    user_email="utilisateur@exemple.com",
    access_level="editors"
)
```

## Cas d'utilisation détaillés

### Navigation et exploration
- `list_organizations`, `list_workspaces`, `list_documents`, `list_tables`, `list_columns`
  * Utilisez pour explorer la structure Grist et découvrir les données disponibles
  * Nécessaires pour obtenir les IDs avant d'exécuter des opérations spécifiques
  * Idéal pour la phase initiale d'analyse des données

### Requêtes et filtrage
- `list_records` : Pour obtenir tous les enregistrements d'une table
- `filter_sql_query` : Pour les filtres simples sur une seule table
- `execute_sql_query` : Pour les requêtes complexes avec jointures et sous-requêtes

### Manipulation des données
- `add_grist_records` et `add_grist_records_safe` : Pour ajouter des données avec ou sans validation
- `update_grist_records` : Pour modifier des enregistrements existants
- `delete_grist_records` : Pour supprimer des enregistrements

### Travail avec les formules
- `get_formula_helpers` : Pour obtenir la syntaxe correcte des références de colonnes
- `validate_formula` : Pour vérifier et corriger automatiquement les formules
- `create_column_with_formula_safe` : Pour créer des colonnes calculées sécurisées

### Export et téléchargement
- `download_document_sqlite`, `download_document_excel`, `download_table_csv` : Pour exporter les données
- `download_attachment` : Pour récupérer les fichiers attachés

### Gestion des accès
- `list_*_access` et `modify_*_access` : Pour administrer les permissions utilisateurs

### Intégrations externes
- `create_webhook`, `modify_webhook` : Pour connecter Grist à d'autres services

## Cas d'utilisation

Le serveur MCP Grist est conçu pour :
- Analyser et résumer les données Grist
- Créer, mettre à jour et supprimer des enregistrements programmatiquement
- Construire des rapports et des visualisations
- Répondre aux questions sur les données stockées
- Connecter Grist avec des modèles de langage pour des requêtes en langage naturel
- Automatiser les flux de travail impliquant des données Grist
- Intégrer Grist à d'autres systèmes via webhooks

## Contribution

Les contributions sont les bienvenues ! Voici comment contribuer :

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité
3. Committez vos changements
4. Poussez vers la branche
5. Ouvrez une Pull Request

## Licence

Ce serveur MCP est sous licence MIT.