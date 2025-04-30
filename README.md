# Grist MCP Server

Un serveur MCP (Model Context Protocol) pour interagir avec l'API Grist. Ce serveur permet d'accéder et de manipuler les données Grist directement depuis des modèles de langage comme Claude.

## Structure du projet

```
mcp-server-grist/
├── docs/                  # Documentation et fichiers de référence
│   └── grist_api.yml      # Documentation de l'API Grist
├── archive/               # Fonctionnalités archivées
│   ├── christmas_order_tool.py     # Outil de commandes de Noël (désactivé)
│   ├── grist_form_tools.py         # Intégration des formulaires (désactivé)
│   └── grist_additional_tools.py    # Outils additionnels (désactivé)
├── grist_mcp_server.py    # Serveur MCP principal
├── requirements.txt       # Dépendances Python
├── setup.py              # Configuration du package
├── Dockerfile            # Configuration Docker
├── .env.template         # Template pour les variables d'environnement
└── README.md             # Documentation
```

## Prérequis

- Python 3.8+
- Une clé API Grist valide
- Les packages Python suivants : `fastmcp`, `httpx`, `pydantic`, `python-dotenv`

## Installation

### Via pip

```bash
pip install mcp-server-grist
```

### Installation manuelle

```bash
git clone https://github.com/yourusername/mcp-server-grist.git
cd mcp-server-grist
pip install -r requirements.txt
```

### Via Docker

```bash
docker build -t mcp/grist-mcp-server .
```

## Configuration

### Variables d'environnement

Créez un fichier `.env` basé sur `.env.template` avec les variables suivantes :
```
GRIST_API_KEY=votre_clé_api
GRIST_API_HOST=https://docs.getgrist.com/api
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

## Fonctionnalités

- Accès aux données Grist directement depuis les modèles de langage
- Liste des organisations, espaces de travail, documents, tables et colonnes
- Gestion des enregistrements (création, lecture, mise à jour, suppression)
- Filtrage et tri des données avec des capacités de requêtage avancées
- Support des requêtes SQL (SELECT uniquement)
- Authentification sécurisée via clé API

## Outils disponibles

### Gestion des organisations et documents
- `list_organizations` : Liste les organisations
- `list_workspaces` : Liste les espaces de travail
- `list_documents` : Liste les documents

### Gestion des tables et colonnes
- `list_tables` : Liste les tables
- `list_columns` : Liste les colonnes
- `list_records` : Liste les enregistrements

### Manipulation des données
- `add_grist_records` : Ajoute des enregistrements
- `update_grist_records` : Met à jour des enregistrements
- `delete_grist_records` : Supprime des enregistrements
- `execute_sql_query` : Exécute une requête SQL (SELECT uniquement)

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

# Liste des enregistrements avec filtrage
records = await list_records(
    doc_id="abc123",
    table_id="Table1",
    filter_json='{"age": [">", 18]}',
    sort="name",
    limit=10
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

# Requête SQL
sql_result = await execute_sql_query(
    doc_id="abc123",
    sql_query="SELECT * FROM Table1 WHERE age > ?",
    parameters=[18]
)
```

## Cas d'utilisation

Le serveur MCP Grist est conçu pour :
- Analyser et résumer les données Grist
- Créer, mettre à jour et supprimer des enregistrements programmatiquement
- Construire des rapports et des visualisations
- Répondre aux questions sur les données stockées
- Connecter Grist avec des modèles de langage pour des requêtes en langage naturel

## Contribution

Les contributions sont les bienvenues ! Voici comment contribuer :

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité
3. Committez vos changements
4. Poussez vers la branche
5. Ouvrez une Pull Request

## Licence

Ce serveur MCP est sous licence MIT.