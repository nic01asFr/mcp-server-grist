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
- `list_records` : Liste les enregistrements avec tri et limite

### Manipulation des données
- `add_grist_records` : Ajoute des enregistrements
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
```

## Cas d'utilisation détaillés

### Fonctions de base
- `list_organizations`, `list_workspaces`, `list_documents`
  * Utilisez pour naviguer dans la structure de Grist
  * Nécessaires pour obtenir les IDs des documents et tables
  * Pas de paramètres complexes

- `list_tables`, `list_columns`
  * Utilisez pour explorer la structure d'un document
  * Utiles pour connaître les noms des colonnes avant de faire des requêtes
  * Pas de paramètres de filtrage

- `list_records`
  * Utilisez pour obtenir tous les enregistrements d'une table
  * Tri simple sur une seule colonne (ex: "name" ou "-age")
  * Limitation du nombre de résultats
  * Ne supporte pas le filtrage (utilisez filter_sql_query à la place)

### Fonctions de filtrage SQL
- `filter_sql_query`
  * Utilisez pour les filtres simples sur une seule table
  * Conditions WHERE basiques (égalité, comparaison)
  * Sélection de colonnes spécifiques
  * Tri et limitation des résultats
  * Exemple : filtrer les employés actifs d'une organisation

- `execute_sql_query`
  * Utilisez pour les requêtes complexes
  * Jointures entre tables
  * Sous-requêtes
  * Agrégations (GROUP BY, HAVING)
  * Paramètres SQL pour la sécurité
  * Timeout personnalisable
  * Exemple : rapports complexes avec jointures

### Fonctions de manipulation
- `add_grist_records`
  * Utilisez pour créer de nouveaux enregistrements
  * Format simple : liste de dictionnaires
  * Pas besoin d'ID (générés automatiquement)
  * Exemple : ajouter de nouveaux clients

- `update_grist_records`
  * Utilisez pour modifier des enregistrements existants
  * Nécessite l'ID de chaque enregistrement
  * Mise à jour partielle possible
  * Exemple : mettre à jour les informations d'un client

- `delete_grist_records`
  * Utilisez pour supprimer des enregistrements
  * Nécessite la liste des IDs à supprimer
  * Opération irréversible
  * Exemple : supprimer des enregistrements obsolètes

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