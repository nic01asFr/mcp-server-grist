# Guide de contribution

Merci de votre intérêt pour contribuer au Grist MCP Server ! Voici comment vous pouvez aider.

## Comment contribuer

1. Forkez le repository
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Poussez vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## Standards de code

- Suivez le style de code existant
- Ajoutez des tests pour les nouvelles fonctionnalités
- Assurez-vous que tous les tests passent
- Mettez à jour la documentation si nécessaire

## Processus de Pull Request

1. Assurez-vous que votre code respecte les standards
2. Mettez à jour la documentation si nécessaire
3. Les PR seront revues par les mainteneurs
4. Les commentaires seront adressés avant la fusion

## Environnement de développement

1. Clonez le repository
2. Installez le paquet et les outils de test :
   ```bash
   pip install -e ".[dev]"
   ```
3. Créez un fichier `.env` basé sur `.env.template`
4. Exécutez les tests :
   ```bash
   python -m pytest tests/
   ```

## Documentation des outils

`docs/tools-reference.mdx` est généré depuis le code. Après avoir ajouté ou modifié
un outil (paramètres, docstring), régénérez-le et citez l'outil dans le README :

```bash
python scripts/generate_tools_reference.py
```

Le test `tests/test_docs.py` échoue si la référence n'est pas à jour, ou si le README
cite un outil ou un paramètre qui n'existe pas.

## Publier une version (mainteneurs)

La branche `official` est la branche de référence. Fusionner dans `official`
ne publie rien : la publication sur PyPI se fait en créant une release GitHub.

1. Dans une Pull Request vers `official` :
   - augmentez `__version__` dans `src/mcp_server_grist/version.py` ;
   - ajoutez une entrée dans `CHANGELOG.md`.
2. Fusionnez la PR une fois les tests au vert.
3. Créez une release GitHub sur `official` avec le tag `v<version>` (ex. `v0.2.2`).

Le workflow `.github/workflows/workflow.yml` relance alors les tests, vérifie que
le tag correspond à la version du code, que le commit appartient à `official` et
que cette version n'est pas déjà sur PyPI, puis publie.
Ne renommez pas ce fichier ni l'environnement `release` : PyPI (Trusted Publisher)
n'accepte que ceux-là.

## Bonnes pratiques

- Écrivez des commits clairs et descriptifs
- Gardez les PR petites et focalisées
- Documentez les changements majeurs
- Respectez le code de conduite

## Code de conduite

- Soyez respectueux et inclusif
- Acceptez les critiques constructives
- Concentrez-vous sur ce qui est le mieux pour la communauté
- Montrez de l'empathie envers les autres membres

## Questions ?

Si vous avez des questions, ouvrez une issue ou contactez les mainteneurs. 