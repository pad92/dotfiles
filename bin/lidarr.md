# Lidarr Script Documentation

## Description

Ce script permet de synchroniser automatiquement Lidarr (gestionnaire de collection musicale) avec Plex (serveur multimédia) et Spotify. Il offre plusieurs fonctionnalités pour gérer les albums, les artistes et les playlists de manière automatisée.

## Fonctionnalités

### 1. Monitorer les albums non monitorés

Active le monitoring pour les albums qui ne sont pas encore surveillés dans Lidarr.

```bash
python3 lidarr.py monitor
```

### 2. Synchroniser les artistes Lidarr avec une collection Plex

Synchronise une collection Plex avec les artistes ayant un tag spécifique dans Lidarr.

```bash
python3 lidarr.py sync-tag "Tag Nom" "Nom Collection"
```

Exemple :
```bash
python3 lidarr.py sync-tag "Favoris" "Mes Albums Préférés"
```

### 3. Désactiver le monitoring des albums en haute qualité

Désactive automatiquement le monitoring pour les albums déjà présents en qualité élevée (FLAC ou MP3 320).

```bash
python3 lidarr.py unmonitor
```

### 4. Synchroniser les likes Spotify vers une playlist Plex

Crée ou met à jour une playlist Plex avec les titres aimés sur Spotify.

```bash
python3 lidarr.py sync-likes
```

## Fichier de configuration

Le script utilise un fichier de configuration YAML nommé `lidarr-config.yml` situé dans le même dossier que le script.

### Structure du fichier de configuration :

```yaml
lidarr:
  url: "http://localhost:8686"  # URL de votre instance Lidarr
  api_key: "votre_cle_api"      # Clé API Lidarr

plex:
  url: "http://localhost:32469" # URL de votre instance Plex
  token: "votre_token_plex"     # Token d'authentification Plex
  library_name: "Music"         # Nom de la bibliothèque musicale Plex
  playlist_name: "Spotify Likes" # Nom de la playlist Plex (optionnel)

spotify:
  client_id: "votre_client_id"      # Client ID Spotify
  client_secret: "votre_client_secret" # Client Secret Spotify
  redirect_uri: "http://localhost:8080/callback" # URI de redirection Spotify
```

## Exemples d'utilisation

### Exemple 1 : Monitorer les albums non surveillés
```bash
python3 lidarr.py monitor
```

### Exemple 2 : Créer une collection Plex à partir d'un tag Lidarr
```bash
python3 lidarr.py sync-tag "Musique Classique" "Classique Collection"
```

### Exemple 3 : Désactiver le monitoring pour les albums en haute qualité
```bash
python3 lidarr.py unmonitor
```

### Exemple 4 : Synchroniser les likes Spotify vers une playlist Plex
```bash
python3 lidarr.py sync-likes
```

## Prérequis

- Python 3.x
- Bibliothèques Python requises :
  - pyyaml
  - requests
  - plexapi
  - spotipy

Installer les dépendances avec :
```bash
pacman -S python-pyaml python-requests python-plexapi python-spotipy
```

## Notes importantes

- Le script nécessite une configuration valide dans le fichier `lidarr-config.yml`
- Pour utiliser la fonction Spotify, vous devez avoir configuré une application Spotify Developer et obtenir les identifiants requis
- Les opérations peuvent prendre un certain temps selon la taille de votre collection musicale

## Option Dry-run

Vous pouvez utiliser l'option `--dry-run` pour simuler l'exécution du script sans effectuer de changements réels :

```bash
python3 lidarr.py --dry-run monitor
python3 lidarr.py --dry-run sync-tag "Tag Nom" "Nom Collection"
python3 lidarr.py --dry-run unmonitor
python3 lidarr.py --dry-run sync-likes
```

Lors de l'utilisation de cette option, le script affichera ce qu'il ferait normalement sans effectuer les appels API réels.
