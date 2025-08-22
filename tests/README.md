# Tests MCP Server Grist

Ce répertoire contient les tests pour le serveur MCP Grist, permettant de valider sa conformité avec les standards MCP et son bon fonctionnement.

## Structure des tests

Les tests sont organisés en plusieurs catégories :

- **Tests unitaires** : Vérifient le fonctionnement individuel des composants
- **Tests d'intégration** : Vérifient l'interaction avec l'API Grist réelle
- **Tests de conformité** : Vérifient la conformité avec le standard MCP
- **Tests de sécurité** : Vérifient les aspects sécuritaires du serveur

## Types de fichiers de test

- `test_client.py` : Tests pour la classe GristClient
- `test_tools.py` : Tests des outils MCP individuels
- `test_transport.py` : Tests des différents modes de transport (stdio, http, sse)
- `test_security.py` : Tests des aspects sécuritaires
- `test_compliance.py` : Tests de conformité au standard MCP
- `test_integration.py` : Tests avec une API Grist réelle

## Exécution des tests

Pour exécuter les tests, utilisez le script `run_tests.py` qui propose plusieurs options :

```bash
# Exécuter tous les tests
python tests/run_tests.py --type all

# Exécuter uniquement les tests unitaires
python tests/run_tests.py --type unit

# Exécuter uniquement les tests d'intégration (requiert une API Grist configurée)
python tests/run_tests.py --type integration
```

## Tests d'intégration

Les tests d'intégration nécessitent une configuration particulière :

1. Créez un fichier `.env` à la racine du projet avec les variables suivantes :
   ```
   GRIST_API_KEY=votre_clé_api_grist
   GRIST_API_HOST=https://docs.getgrist.com/api  # ou votre instance Grist
   ```

2. Les tests d'intégration utilisent ces variables pour se connecter à l'API Grist et effectuer des opérations réelles.

3. **Note importante** : Les tests sont conçus pour être non destructifs, mais ils peuvent lire des données réelles. Les tests qui modifient des données sont commentés par défaut.

## Intégration Continue

Les tests unitaires et de conformité sont automatiquement exécutés via GitHub Actions à chaque push ou pull request. Les tests d'intégration sont désactivés en CI car ils nécessitent des identifiants d'API.

## Couverture de code

La couverture de code est mesurée lors de l'exécution des tests en CI et téléchargée vers Codecov pour analyse.
