# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Non publié]

### Documentation

- README en anglais (page PyPI et GitHub), restructuré : démarrage rapide, tableau des
  variables d'environnement, options HTTP, Docker, outils, exemples, développement.
  Version française complète dans `README.fr.md`, avec lien entre les deux.
- Corrige le lien `git clone` (pointait vers un autre dépôt), supprime les sections en
  double et le logo Grist (le projet n'est pas un produit officiel Grist).
- `tests/test_docs.py` vérifie les deux README.
- Site public généré (`site/`, publié sur GitHub Pages par `.github/workflows/pages.yml`) :
  page de présentation en français et en anglais (installation par client, comparaison
  avec le serveur MCP officiel de Grist, outils, projets liés, référencement). Deux thèmes,
  au choix du visiteur : La Suite numérique (couleurs de grist.numerique.gouv.fr, par défaut)
  et Grist (couleurs de getgrist.com, thème du kit Widgets-Grist), en clair et en sombre,
  contrastes vérifiés (WCAG AA).
- Fichiers pour agents générés depuis les outils : `llms.txt`, `SKILL.md`,
  `fiche-capacites.json` et `commandes.json` (contrats `fiche-capacites-0.1` et
  `commandes-0.1` de Widgets-Grist). Source éditoriale : `docs/vitrine.json` ;
  générateur : `scripts/generate_site.py` ; garde-fous : `tests/test_site.py`.
- README : sections « For AI agents / Pour les agents IA » et « Related projects / Projets liés ».

## [0.2.2] - 2026-11-08

Correctifs des outils de schéma et de colonnes, du démarrage et de Docker, vérifiés sur une vraie
instance Grist (grist-core 1.7.22, et 1.1.10 pour la compatibilité).
Aucun paramètre d'outil ne change ; les réponses gagnent seulement des
clés (`warnings`, `columns`, `reverse_column.two_way`).

### Corrigé

- **Colonne affichée des références** (`create_schema`, `create_reference_column`,
  `create_column`, `modify_column`) : la formule d'affichage est désormais posée.
  Auparavant `visibleCol` était enregistré mais Grist affichait l'identifiant de ligne.
- **Relation inverse (`reverse` / `reverse_column`)** : utilise la référence à double
  sens native de Grist (`AddReverseColumn`), synchronisée et remplie automatiquement.
  Auparavant une colonne RefList indépendante et vide était créée (libellé « Tachess »).
  Sur une instance Grist trop ancienne, repli sur une colonne calculée
  (`lookupRecords`) en lecture seule, avec avertissement.
- **`untieColIdFromLabel` et `description`** : appliqués après la création, car Grist
  les ignore à la création (AddTable/AddColumn). Changer un libellé ne renomme plus l'ID.
- **`create_table`** : la clé `choices` d'une colonne est fusionnée dans `widgetOptions`
  (auparavant : erreur HTTP 400). Les IDs réellement attribués par Grist sont renvoyés
  (`columns`) et signalés s'ils diffèrent ; le libellé garde l'ID demandé (« Prénom »).
- **`create_schema`** :
  - la notation `"Ref:Table"` / `"RefList:Table"` est traitée comme une référence
    (auparavant créée comme colonne simple, sans colonne affichée) ;
  - relancer le même schéma ne crée plus de doublons : les tables existantes ne sont
    jamais modifiées (ni colonnes, ni références, ni données) ;
  - avec `skip_existing=False`, échoue sans rien créer si une table existe déjà ;
  - les `widgetOptions` des colonnes du schéma sont appliquées.
- **`validate_schema`** : vérifie que la colonne `visible` existe dans la table cible et
  que la colonne `reverse` n'existe pas déjà ; signale une référence sans `visible`.
- **`create_reference_column`** : une erreur d'accès à l'API (clé, réseau) n'est plus
  présentée comme « table cible inexistante » ; la table source est vérifiée.

- **Démarrage / arrêt du serveur** : le mode stdio ne plante plus à l'arrêt, et le mode
  `sse` démarre (il échouait sur le paramètre `mount_path`, inconnu de FastMCP).
- **Image Docker** (ticket #14) : le paquet est installé dans l'image et lancé par la
  commande `mcp-server-grist` (auparavant : `No module named grist_mcp_server`).
  L'image tourne sans les droits root et n'embarque plus `.env` ni `.git`.
- **README** : configuration Claude Desktop (module `mcp_server_grist`), exemples Docker
  (`-i` au lieu de `-it`, mode HTTP avec `--host 0.0.0.0`), fichier `.env.template`.
- **Sécurité** : inclut le correctif d'injection SQL dans `order_by` de `filter_sql_query`
  (fusionné après la 0.2.1, jamais publié jusqu'ici).

### Modifié

- Dépendance `fastmcp>=2.14,<5` (vérifiée sur 2.14, 3.0, 3.4 et 4.1 ; les versions
  antérieures ne s'installent plus avec pydantic actuel).
- Publication sur PyPI déclenchée par une release GitHub (et non plus par chaque push
  sur `official`), après les tests et des contrôles de version. Voir `CONTRIBUTING.md`.
- Workflows : suppression des doublons et fichiers obsolètes ; tests sur Python 3.10 à 3.13.
- Tests : suppression des tests de l'ancien module `grist_mcp_server`, réécriture de
  `test_security.py` et `test_transport.py` pour le code actuel. Suite entièrement au vert.

### Ajouté

- `GristClient.apply_user_actions(doc_id, actions)` : appel de `POST /docs/{doc}/apply`.
- Tests `tests/test_schema_tools.py`.
- Dépendances de test : `pip install -e ".[dev]"`.
- `docs/tools-reference.mdx` : référence complète des 54 outils, générée depuis le code
  (`scripts/generate_tools_reference.py`) ; un test vérifie qu'elle reste à jour, et que
  le README ne cite que des outils et des paramètres existants.

### Documentation

- README (page PyPI) : liste des outils alignée sur les 54 outils réels (ajout des outils
  de schéma, retrait de 5 outils inexistants), exemples corrigés, Python 3.10+,
  configuration Claude Desktop sans le wrapper Node.js.
- `docs/index.mdx` réécrit (liens vers ce dépôt, Python 3.10+).
- Auteur du paquet : `nic01asFr`.

### Supprimé

- `npm-wrapper/` : jamais publié sur npm, son nom (`@modelcontextprotocol/server-grist`)
  n'était pas disponible. Les modes `uvx`, `pip` et Docker le remplacent.
- `docker-compose.yml` : clé `version` obsolète, réseau inutilisé, `tty` (gênant en stdio).

## [0.2.1] - 2026-02-21

### Modifié

- Python 3.10 minimum (`requires-python = ">=3.10"`).
- README : utilisation à la volée avec `uvx`, URL du dépôt.
- `docker-compose.yml` : retrait du service SSE.

## [0.2.0] - 2025-12-30

### Corrigé

- Le paramètre `ctx` n'est plus exposé aux clients MCP : il n'est plus nécessaire de
  passer `ctx=null` à chaque appel d'outil.

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

Note : dans cette version, `visible_col`, `untie_col_id_from_label` et `description`
étaient transmis à Grist mais sans effet réel ; ils ne fonctionnent que depuis la 0.2.2.

### Structure du projet

```
src/mcp_server_grist/
├── types.py              # NOUVEAU: Types et validations
├── tools/
│   ├── __init__.py       # MODIFIÉ: Exports
│   ├── utils.py          # NOUVEAU: Utilitaires
│   ├── administration.py # MODIFIÉ: Corrections
│   ├── schema.py         # NOUVEAU: Outils schéma
│   └── export.py         # MODIFIÉ: Corrections
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
