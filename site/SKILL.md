---
name: mcp-server-grist
description: "mcp-server-grist : Serveur MCP qui donne à un assistant IA l'accès à l'API Grist avec une simple clé API : parcourir les documents, interroger les tables en SQL, ajouter et modifier des enregistrements, créer des tables, des colonnes et des schémas complets avec leurs relations. Fonctionne sur toute instance Grist."
---

# mcp-server-grist

Serveur MCP qui donne à un assistant IA l'accès à l'API Grist avec une simple clé API : parcourir les documents, interroger les tables en SQL, ajouter et modifier des enregistrements, créer des tables, des colonnes et des schémas complets avec leurs relations. Fonctionne sur toute instance Grist.

Version 0.2.2. Généré depuis `fiche-capacites.json` (contrat fiche-capacites-0.1) et `commandes.json` : ne pas modifier à la main.

## Interfaces

- ce skill : disponible.
- ligne de commande : non disponible.
- serveur MCP : disponible.
- page WebMCP : non disponible.
- page de présentation : disponible.

Lancer le serveur : `uvx mcp-server-grist` (stdio), avec les variables `GRIST_API_KEY` et `GRIST_API_URL`.

## Outils

### configurer

- `list_organization_access` : Liste les utilisateurs ayant accès à une organisation.
  Entrée requise : `org_id` ; appelle l’API Grist ; n’écrit rien.
- `modify_organization_access` : Modifie l'accès d'un utilisateur à une organisation.
  Entrée requise : `org_id`, `user_email`, `access_level` ; appelle l’API Grist ; écrit : les droits d'accès d'une organisation.
- `list_workspace_access` : Liste les utilisateurs ayant accès à un espace de travail.
  Entrée requise : `workspace_id` ; appelle l’API Grist ; n’écrit rien.
- `modify_workspace_access` : Modifie l'accès d'un utilisateur à un espace de travail.
  Entrée requise : `workspace_id`, `user_email`, `access_level` ; appelle l’API Grist ; écrit : les droits d'accès d'un espace de travail.
- `list_document_access` : Liste les utilisateurs ayant accès à un document.
  Entrée requise : `doc_id` ; appelle l’API Grist ; n’écrit rien.
- `modify_document_access` : Modifie l'accès d'un utilisateur à un document.
  Entrée requise : `doc_id`, `user_email`, `access_level` ; appelle l’API Grist ; écrit : les droits d'accès d'un document.
- `list_webhooks` : Liste les webhooks d'un document Grist.
  Entrée requise : `doc_id` ; appelle l’API Grist ; n’écrit rien.
- `create_webhook` : Crée un webhook pour un document Grist.
  Entrée requise : `doc_id`, `url` ; appelle l’API Grist ; écrit : un webhook.
- `modify_webhook` : Modifie un webhook existant.
  Entrée requise : `doc_id`, `webhook_id` ; appelle l’API Grist ; écrit : un webhook.
- `delete_webhook` : Supprime un webhook.
  Entrée requise : `doc_id`, `webhook_id` ; appelle l’API Grist ; écrit : supprime un webhook.
- `clear_webhook_queue` : Vide la file d'attente des webhooks pour un document.
  Entrée requise : `doc_id` ; appelle l’API Grist ; écrit : vide la file d'attente des webhooks.

### creer

- `create_workspace` : Crée un nouvel espace de travail dans une organisation.
  Entrée requise : `org_id`, `name` ; appelle l’API Grist ; écrit : un espace de travail.
- `create_document` : Crée un nouveau document dans un espace de travail.
  Entrée requise : `workspace_id`, `name` ; appelle l’API Grist ; écrit : un document.

### editer

- `add_grist_records` : Ajoute des enregistrements à une table Grist.
  Entrée requise : `doc_id`, `table_id`, `records` ; appelle l’API Grist ; écrit : des enregistrements.
- `add_grist_records_safe` : Ajoute des enregistrements avec validation préalable de la structure.
  Entrée requise : `doc_id`, `table_id`, `records` ; appelle l’API Grist ; écrit : des enregistrements.
- `update_grist_records` : Met à jour des enregistrements existants dans une table Grist.
  Entrée requise : `doc_id`, `table_id`, `records` ; appelle l’API Grist ; écrit : des enregistrements.
- `delete_grist_records` : Supprime des enregistrements d'une table Grist.
  Entrée requise : `doc_id`, `table_id`, `record_ids` ; appelle l’API Grist ; écrit : supprime des enregistrements.
- `modify_organization` : Modifie les propriétés d'une organisation.
  Entrée requise : `org_id` ; appelle l’API Grist ; écrit : une organisation.
- `delete_organization` : Supprime une organisation.
  Entrée requise : `org_id` ; appelle l’API Grist ; écrit : supprime une organisation et tout son contenu.
- `modify_workspace` : Modifie les propriétés d'un espace de travail.
  Entrée requise : `workspace_id` ; appelle l’API Grist ; écrit : un espace de travail.
- `delete_workspace` : Supprime un espace de travail.
  Entrée requise : `workspace_id` ; appelle l’API Grist ; écrit : supprime un espace de travail et ses documents.
- `modify_document` : Modifie les propriétés d'un document.
  Entrée requise : `doc_id` ; appelle l’API Grist ; écrit : un document.
- `delete_document` : Supprime un document.
  Entrée requise : `doc_id` ; appelle l’API Grist ; écrit : supprime un document.
- `move_document` : Déplace un document vers un autre espace de travail.
  Entrée requise : `doc_id`, `target_workspace_id` ; appelle l’API Grist ; écrit : l'emplacement d'un document.
- `force_reload_document` : Force le rechargement d'un document.
  Entrée requise : `doc_id` ; appelle l’API Grist ; écrit : recharge un document (sans modifier ses données).
- `delete_document_history` : Supprime l'historique d'un document, ne conservant que les dernières actions.
  Entrée requise : `doc_id` ; appelle l’API Grist ; écrit : supprime l'historique d'un document.
- `upload_attachment` : Téléverse une pièce jointe dans un document Grist.
  Entrée requise : `doc_id`, `filename`, `content_base64` ; appelle l’API Grist ; écrit : une pièce jointe.

### structurer

- `create_table` : Crée une nouvelle table dans un document.
  Entrée requise : `doc_id`, `table_id` ; appelle l’API Grist ; écrit : une table et ses colonnes.
- `modify_table` : Modifie les propriétés d'une table.
  Entrée requise : `doc_id`, `table_id` ; appelle l’API Grist ; écrit : l'identifiant d'une table.
- `create_column` : Crée une nouvelle colonne dans une table.
  Entrée requise : `doc_id`, `table_id`, `column_id` ; appelle l’API Grist ; écrit : une colonne.
- `modify_column` : Modifie les propriétés d'une colonne.
  Entrée requise : `doc_id`, `table_id`, `column_id` ; appelle l’API Grist ; écrit : une colonne.
- `delete_column` : Supprime une colonne d'une table.
  Entrée requise : `doc_id`, `table_id`, `column_id` ; appelle l’API Grist ; écrit : supprime une colonne et ses données.
- `create_reference_column` : Crée une colonne de référence qui affiche la colonne choisie de la table cible.
  Entrée requise : `doc_id`, `table_id`, `column_id`, `target_table`, `visible_column` ; appelle l’API Grist ; écrit : une colonne référence (et sa colonne inverse si demandé).
- `validate_schema` : Valide un schéma sans le créer.
  Entrée requise : `doc_id`, `schema` ; appelle l’API Grist ; n’écrit rien.
- `create_schema` : Crée un schéma complet avec tables, colonnes et relations.
  Entrée requise : `doc_id`, `schema` ; appelle l’API Grist ; écrit : des tables, colonnes, références et enregistrements.

### exploiter

- `list_organizations` : Liste toutes les organisations Grist accessibles.
  Entrée requise : aucune ; appelle l’API Grist ; n’écrit rien.
- `describe_organization` : Obtient des informations détaillées sur une organisation spécifique.
  Entrée requise : `org_id` ; appelle l’API Grist ; n’écrit rien.
- `list_workspaces` : Liste tous les espaces de travail dans une organisation Grist.
  Entrée requise : `org_id` ; appelle l’API Grist ; n’écrit rien.
- `describe_workspace` : Obtient des informations détaillées sur un espace de travail spécifique.
  Entrée requise : `workspace_id` ; appelle l’API Grist ; n’écrit rien.
- `list_documents` : Liste tous les documents dans un espace de travail Grist.
  Entrée requise : `workspace_id` ; appelle l’API Grist ; n’écrit rien.
- `describe_document` : Obtient des informations détaillées sur un document spécifique.
  Entrée requise : `doc_id` ; appelle l’API Grist ; n’écrit rien.
- `list_tables` : Liste toutes les tables dans un document Grist.
  Entrée requise : `doc_id` ; appelle l’API Grist ; n’écrit rien.
- `list_columns` : Liste toutes les colonnes dans une table Grist.
  Entrée requise : `doc_id`, `table_id` ; appelle l’API Grist ; n’écrit rien.
- `list_records` : Liste les enregistrements dans une table Grist avec tri et limitation optionnels.
  Entrée requise : `doc_id`, `table_id` ; appelle l’API Grist ; n’écrit rien.
- `get_table_schema` : Obtient le schéma détaillé d'une table Grist.
  Entrée requise : `doc_id`, `table_id` ; appelle l’API Grist ; n’écrit rien.
- `filter_sql_query` : Exécute une requête SQL de filtrage sur une table Grist.
  Entrée requise : `doc_id`, `table_id` ; appelle l’API Grist ; n’écrit rien.
- `execute_sql_query` : Exécute une requête SQL personnalisée sur un document Grist.
  Entrée requise : `doc_id`, `sql_query` ; appelle l’API Grist ; n’écrit rien.
- `download_document_sqlite` : Télécharge un document Grist au format SQLite.
  Entrée requise : `doc_id` ; appelle l’API Grist ; n’écrit rien.
- `download_document_excel` : Télécharge un document Grist au format Excel.
  Entrée requise : `doc_id` ; appelle l’API Grist ; n’écrit rien.
- `download_table_csv` : Télécharge une table Grist au format CSV.
  Entrée requise : `doc_id`, `table_id` ; appelle l’API Grist ; n’écrit rien.
- `list_attachments` : Liste les pièces jointes d'un document Grist.
  Entrée requise : `doc_id` ; appelle l’API Grist ; n’écrit rien.
- `get_attachment_info` : Obtient les métadonnées d'une pièce jointe.
  Entrée requise : `doc_id`, `attachment_id` ; appelle l’API Grist ; n’écrit rien.
- `download_attachment` : Télécharge le contenu d'une pièce jointe.
  Entrée requise : `doc_id`, `attachment_id` ; appelle l’API Grist ; n’écrit rien.
- `export_schema` : Exporte le schéma d'un document existant.
  Entrée requise : `doc_id` ; appelle l’API Grist ; n’écrit rien.

## Non couvert

Verbes sans outil : presenter, personnaliser, publier, recolter, traiter.

## Limites

- Chaque outil agit avec la clé API Grist configurée : il a exactement les droits de la personne qui la possède.
- Les requêtes SQL sont en lecture seule (SELECT uniquement).
- Les pages, vues et widgets d'un document ne se pilotent pas par ces outils.
- Pas d'outil de présentation : commencer par list_organizations, puis descendre la hiérarchie organisation, espace de travail, document, table.
- Les noms d'outils ne portent pas de préfixe : ils sont conservés tels quels pour ne pas casser les installations existantes.
- Les exemples des commandes donnent l'entrée d'un appel minimal ; la sortie dépend du document et n'est pas reproduite.

## Règles d’écriture

- Commencer par `list_organizations`, puis descendre la hiérarchie (espace de travail, document, table) pour obtenir des identifiants réels.
- Ne citer que les outils listés ci-dessous, avec leur nom exact ; ne jamais en inventer un.
- Donner à chaque outil une entrée conforme à son schéma ; en cas d’erreur, relire le message et corriger l’entrée plutôt que réessayer à l’identique.
- Écrire en français, sans jargon, dès que le résultat est destiné à une personne.
- Annoncer à la personne ce qui sera écrit dans un document avant de l’écrire, et seulement quand l’outil est marqué comme écrivant ; demander confirmation avant toute suppression.

## Interdits

- Ne jamais promettre un refus côté serveur des valeurs invalides : sans contrôle dans le document, une valeur invalide est acceptée.
- Ne jamais deviner un identifiant de document, de table ou de colonne : le demander ou le lire.
- Ne jamais présenter comme fait un verbe de la section « Non couvert » : le dire, et proposer l’interface qui le couvre quand il en existe une.
- Ne jamais publier ni envoyer ailleurs sans l’accord explicite de la personne.
