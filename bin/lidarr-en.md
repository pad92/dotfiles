# Lidarr Script Documentation

## Description

This script allows automatic synchronization between Lidarr (music collection manager) and Plex (media server) as well as Spotify. It provides several features to manage albums, artists, and playlists automatically.

## Features

### 1. Monitor unmonitored albums

Enable monitoring for albums that are not yet monitored in Lidarr.

```bash
python3 lidarr.py monitor
```

### 2. Synchronize Lidarr artists with a Plex collection

Synchronize a Plex collection with artists having a specific tag in Lidarr.

```bash
python3 lidarr.py sync-tag "Tag Name" "Collection Name"
```

Example:
```bash
python3 lidarr.py sync-tag "Favorites" "My Favorite Albums"
```

### 3. Disable monitoring for high quality albums

Automatically disable monitoring for albums already present in high quality (FLAC or MP3 320).

```bash
python3 lidarr.py unmonitor
```

### 4. Synchronize Spotify likes to a Plex playlist

Create or update a Plex playlist with liked tracks from Spotify.

```bash
python3 lidarr.py sync-likes
```

## Configuration File

The script uses a YAML configuration file named `lidarr-config.yml` located in the same directory as the script.

### Configuration file structure:

```yaml
lidarr:
  url: "http://localhost:8686"  # URL of your Lidarr instance
  api_key: "your_api_key"       # Lidarr API key

plex:
  url: "http://localhost:32469" # URL of your Plex instance
  token: "your_plex_token"      # Plex authentication token
  library_name: "Music"         # Name of Plex music library
  playlist_name: "Spotify Likes" # Name of Plex playlist (optional)

spotify:
  client_id: "your_client_id"       # Spotify Client ID
  client_secret: "your_client_secret" # Spotify Client Secret
  redirect_uri: "http://localhost:8080/callback" # Spotify Redirect URI
```

## Usage Examples

### Example 1: Monitor unmonitored albums
```bash
python3 lidarr.py monitor
```

### Example 2: Create a Plex collection from a Lidarr tag
```bash
python3 lidarr.py sync-tag "Classical Music" "Classical Collection"
```

### Example 3: Disable monitoring for high quality albums
```bash
python3 lidarr.py unmonitor
```

### Example 4: Synchronize Spotify likes to a Plex playlist
```bash
python3 lidarr.py sync-likes
```

## Prerequisites

- Python 3.x
- Required Python libraries:
  - pyyaml
  - requests
  - plexapi
  - spotipy

Install dependencies with:
```bash
pacman -S python-pyaml python-requests python-plexapi python-spotipy
```

## Important Notes

- The script requires a valid configuration in the `lidarr-config.yml` file
- To use the Spotify function, you must have configured a Spotify Developer application and obtained the required credentials
- Operations may take some time depending on the size of your music collection

## Dry-run Option

You can use the `--dry-run` option to simulate script execution without making actual changes:

```bash
python3 lidarr.py --dry-run monitor
python3 lidarr.py --dry-run sync-tag "Tag Name" "Collection Name"
python3 lidarr.py --dry-run unmonitor
python3 lidarr.py --dry-run sync-likes
```

When using this option, the script will display what it would normally do without making actual API calls.
