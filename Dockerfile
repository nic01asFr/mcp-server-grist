FROM python:3.12-slim

# Définir des variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV LOG_LEVEL=INFO

# Créer et définir le répertoire de travail
WORKDIR /app

# Copier le projet et installer le paquet (dépendances comprises).
# Le paquet est sous src/ : il doit être installé pour être importable.
COPY pyproject.toml setup.py README.md LICENSE MANIFEST.in requirements.txt ./
COPY src ./src
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir . && \
    rm -rf build src/*.egg-info && \
    useradd --create-home --uid 10001 mcp

# Exécuter sans les droits root
USER mcp

# Exposer les ports pour les modes HTTP
EXPOSE 8000

# Configuration de Grist :
# - GRIST_API_KEY : clé API (obligatoire)
# - GRIST_API_URL : URL de l'API, prioritaire (ex. https://docs.getgrist.com/api)
# - GRIST_API_HOST : utilisée si GRIST_API_URL n'est pas définie
ENV GRIST_API_KEY=""
ENV GRIST_API_HOST="https://grist.numerique.gouv.fr/api"

# Point d'entrée : la commande installée par le paquet
ENTRYPOINT ["mcp-server-grist"]

# Par défaut, utiliser le mode stdio
CMD ["--transport", "stdio"]

# Exemples d'utilisation du conteneur:
# Mode stdio (par défaut):
#   docker run --rm -i -e GRIST_API_KEY=your_key mcp/grist-mcp-server
#
# Mode streamable-http (--host 0.0.0.0 est nécessaire dans un conteneur):
#   docker run --rm -p 8000:8000 -e GRIST_API_KEY=your_key mcp/grist-mcp-server \
#     --transport streamable-http --host 0.0.0.0
#
# Autre instance Grist:
#   docker run --rm -i -e GRIST_API_KEY=your_key \
#     -e GRIST_API_URL=https://docs.getgrist.com/api mcp/grist-mcp-server
