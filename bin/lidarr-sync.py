#!/usr/bin/env python3
import requests
import sys
import yaml
import os
import argparse
from plexapi.server import PlexServer

# ================= GESTION DYNAMIQUE DU FICHIER CONFIG =================
# Récupère le chemin absolu du script et replace l'extension par .yml
SCRIPT_PATH = os.path.abspath(__file__)
CONFIG_FILE = os.path.splitext(SCRIPT_PATH)[0] + "-config.yml"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Erreur : Le fichier de configuration est introuvable.")
        print(f"Attendu : {CONFIG_FILE}")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier YAML : {e}")
        sys.exit(1)

# ================= LOGIQUE PRINCIPALE =================

def get_lidarr_artists_by_tag(config, tag_name):
    """Récupère la liste des artistes depuis Lidarr via le tag."""
    headers = {"X-Api-Key": config['lidarr']['api_key']}
    base_url = config['lidarr']['url']

    try:
        r = requests.get(f"{base_url}/api/v1/tag", headers=headers)
        r.raise_for_status()
        tag_id = next((t['id'] for t in r.json() if t['label'].lower() == tag_name.lower()), None)

        if tag_id is None:
            print(f"Erreur: Le tag '{tag_name}' n'existe pas dans Lidarr.")
            return []

        r = requests.get(f"{base_url}/api/v1/artist", headers=headers)
        r.raise_for_status()
        return [a['artistName'] for a in r.json() if tag_id in a.get('tags', [])]

    except Exception as e:
        print(f"Erreur Lidarr: {e}")
        return []

def sync_plex_collection(config, lidarr_names, collection_name):
    """Synchronise la collection Plex (API à jour)."""
    try:
        plex = PlexServer(config['plex']['url'], config['plex']['token'])
        music_lib = plex.library.section(config['plex']['library_name'])
    except Exception as e:
        print(f"Erreur de connexion Plex: {e}")
        sys.exit(1)

    all_plex_artists = music_lib.all()
    plex_artist_map = {artist.title.lower(): artist for artist in all_plex_artists}

    artists_to_collect = [plex_artist_map[n.lower()] for n in lidarr_names if n.lower() in plex_artist_map]

    collections = music_lib.collections(title=collection_name)

    if collections:
        collection = collections[0]
        print(f"Mise à jour de la collection : '{collection_name}'")

        current_collection_items = collection.items() # Corrected method
        current_set = set(item.ratingKey for item in current_collection_items)
        target_set = set(item.ratingKey for item in artists_to_collect)

        to_add = [a for a in artists_to_collect if a.ratingKey not in current_set]
        to_remove = [a for a in current_collection_items if a.ratingKey not in target_set]

        if to_add: collection.addItems(to_add)
        if to_remove: collection.removeItems(to_remove)

        print(f"Résultat : +{len(to_add)} / -{len(to_remove)} artistes.")
    else:
        print(f"Création de la collection : '{collection_name}'")
        if artists_to_collect:
            music_lib.createCollection(title=collection_name, items=artists_to_collect)
            print(f"Succès : {len(artists_to_collect)} artistes ajoutés.")

def main():
    parser = argparse.ArgumentParser(description="Sync Lidarr Tag to Plex Collection")
    parser.add_argument("tag", help="Nom du tag Lidarr")
    parser.add_argument("collection", help="Nom de la collection Plex")

    args = parser.parse_args()
    config = load_config()

    print(f"--- Sync : Lidarr[{args.tag}] to Plex[{args.collection}] ---")

    lidarr_names = get_lidarr_artists_by_tag(config, args.tag)

    if not lidarr_names:
        return

    sync_plex_collection(config, lidarr_names, args.collection)

if __name__ == "__main__":
    main()
