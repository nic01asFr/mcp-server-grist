# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-12-30

### Ajouté

- **Nouvel outil `create_schema`** : Création de schémas complets en une opération
  - Création séquentielle : tables simples → résolution refs → colonnes référence
  - Support des relations inverses (`reverse` dans la définition)
  - Insertion optionnelle de données initiales
  - Rapport détaillé avec warnings et erreurs

- **Nouvel outil `create_reference_column`** : Création de références simplifiée
  - Résolution automatique de `visibleCol` par nom de colonne
  - Validation de l'existence de la table cible
  - Création optionnelle de la relation inverse

- **Nouvel outil `validate_schema`** : Validation sans création
  - Vérification des tables cibles
  - Détection des colonnes Choice sans choix
  - Liste des erreurs et warnings

- **Nouvel outil `export_schema`** : Export de schémas existants
  - Formats : JSON, YAML, Mermaid (diagramme ER)
  - Option pour inclure les données

- **Nouveau module `types.py`** : Définitions de types
  - `ColumnDefinition`, `TableDefinition`, `SchemaDefinition`
  - Mapping `GRIST_COLUMN_TYPES` avec validations
  - Fonction `parse_schema_dict` pour parser les schémas

- **Nouveau module `utils.py`** : Fonctions utilitaires
  - `prepare_table_payload` : Format correct pour création de tables
  - `prepare_column_payload` : Format correct pour colonnes
  - `resolve_visible_col` : Résolution nom → colRef
  - `check_table_exists` : Vérification d'existence

### Corrigé

- **`create_table`** : Format du payload corrigé
  - Avant : `{"tables": [{"tableId": "X", "columns": [...]}]}`
  - Après : `{"tables": [{"id": "X", "columns": [{"id": "col", "fields": {...}}]}]}`

- **`modify_table`** : Format du payload corrigé
  - Avant : `{"tables": [{"tableId": "X", "newTableId": "Y"}]}`
  - Après : `{"tables": [{"id": "X", "fields": {"tableId": "Y"}}]}`

- **`create_column` / `modify_column`** : `widgetOptions` sérialisé en JSON string
  - L'API Grist attend une string, pas un dict
  - Correction appliquée via `json.dumps()`

- **`create_column`** : Support des `choices` pour `Choice`/`ChoiceList`
  - Nouveau paramètre `choices: List[str]`
  - Intégré automatiquement dans `widgetOptions`

- **`download_table_csv`** : Implémentation complète
  - Paramètre `tableId` correctement passé

- **`download_document_excel`** : Gestion du paramètre obligatoire `tableId`
  - Récupère automatiquement la première table si non spécifié

### Modifié

- **`create_column`** : Nouveaux paramètres
  - `visible_col: int` : Pour les références
  - `untie_col_id_from_label: bool` : Défaut True
  - `description: str` : Description de la colonne
  - `choices: List[str]` : Pour Choice/ChoiceList

- **`modify_column`** : Nouveaux paramètres
  - `visible_col: int`
  - `untie_col_id_from_label: bool`
  - `description: str`

### Structure du projet

```
src/mcp_server_grist/
├── types.py              # NOUVEAU: Types et validations
├── tools/
│   ├── __init__.py       # MODIFIÉ: Exports
│   ├── utils.py          # NOUVEAU: Utilitaires
│   ├── administration.py # MODIFIÉ: Corrections
│   ├── schema.py         # NOUVEAU: Outils schéma
│   └── downloads.py      # MODIFIÉ: Corrections
└── ...
```

## [0.1.x] - Versions précédentes

### Fonctionnalités initiales

- Navigation : organisations, workspaces, documents, tables, colonnes
- CRUD tables et colonnes
- CRUD enregistrements
- Requêtes SQL
- Gestion des accès
- Webhooks
- Pièces jointes
