# Politique de sécurité

## Signalement de vulnérabilités

Si vous découvrez une vulnérabilité de sécurité, merci de nous la signaler via Github.
## Mesures de sécurité

### Authentification et autorisation
- Utilisation de clés API Grist pour l'authentification
- Principe du moindre privilège appliqué aux accès
- Validation stricte des entrées utilisateur

### Protection des données
- Les clés API sont stockées de manière sécurisée
- Les données sensibles sont masquées dans les logs
- Communication chiffrée avec l'API Grist

### Sécurité du code
- Validation des entrées pour toutes les requêtes API
- Gestion sécurisée des erreurs
- Tests de sécurité réguliers

## Bonnes pratiques recommandées

1. Ne jamais exposer votre clé API Grist publiquement
2. Utiliser des variables d'environnement pour les informations sensibles
3. Mettre à jour régulièrement les dépendances
4. Vérifier les logs pour détecter des activités suspectes

## Responsabilités

- Les utilisateurs sont responsables de la sécurité de leurs clés API
- Les contributeurs doivent suivre les bonnes pratiques de sécurité
- Les mainteneurs s'engagent à répondre rapidement aux signalements de vulnérabilités 