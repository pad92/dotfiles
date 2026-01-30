#!/usr/bin/env python3
"""
Lidarr and Plex synchronization script for managing music library monitoring and organization.

CHANGELOG:

2026-01-30:
- Added progress indicator for artist analysis in unmonitor operation
- Enhanced error messages to include artist names and IDs for better debugging
- Added graceful Ctrl+C handling with signal interruption support
- Added confirmation prompt when Ctrl+C is pressed

2026-01-30:
- Added dry-run functionality (--dry-run flag) to simulate execution without making changes
- Implemented comprehensive error handling for malformed API responses
- Added type checking and data validation for album and artist data
- Updated documentation files with dry-run usage information

2026-01-29:
- Initial implementation of lidarr.py script with full functionality
- Support for monitor, sync-tag, unmonitor, and sync-likes commands
- Integration with Lidarr, Plex, and Spotify APIs
- Configuration file handling and validation
"""

import os
import sys
import yaml
import requests
import time
import argparse
import logging
import signal
from typing import Dict, List, Optional, Any, Tuple
from plexapi.server import PlexServer
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================= DYNAMIC CONFIG FILE HANDLING =================
SCRIPT_PATH = os.path.abspath(__file__)
CONFIG_FILE = os.path.splitext(SCRIPT_PATH)[0] + "-config.yml"

def load_config() -> Dict[str, Any]:
    """
    Load the YAML configuration file.

    Returns:
        Dict[str, Any]: Configuration dictionary

    Raises:
        SystemExit: If configuration file is not found or invalid
    """
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"Configuration file not found: {CONFIG_FILE}")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Validate required configuration sections
        required_sections = ['lidarr', 'plex']
        for section in required_sections:
            if section not in config:
                logger.error(f"Missing required configuration section: {section}")
                sys.exit(1)

        return config
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading configuration file: {e}")
        sys.exit(1)

def is_quality_satisfied(api_base: str, headers: Dict[str, str], album: Dict[str, Any]) -> bool:
    """
    Check if the album is already complete in FLAC or MP3 320.

    Args:
        api_base (str): Base URL for Lidarr API
        headers (Dict[str, str]): HTTP headers with API key
        album (Dict[str, Any]): Album data from Lidarr

    Returns:
        bool: True if album quality is satisfactory, False otherwise
    """
    # Validate album data
    if not album:
        return False

    stats = album.get('statistics', {})

    # 1. If the album is not 100% tracks present, it is not satisfactory
    if stats.get('percentOfTracks', 0) < 100:
        return False

    # 2. If 100%, check the quality of existing files
    album_id = album.get('id')
    if not album_id:
        return False

    try:
        # Retrieve track files for this album
        res = requests.get(
            f"{api_base}/trackfile",
            params={"albumId": album_id},
            headers=headers,
            timeout=30
        )
        res.raise_for_status()
        files = res.json()

        if not files:
            return False

        for f in files:
            quality_name = f.get('quality', {}).get('quality', {}).get('name', '').upper()
            # Check if the quality contains target keywords
            is_flac = "FLAC" in quality_name or "LOSSLESS" in quality_name
            is_320 = "320" in quality_name

            if not (is_flac or is_320):
                # If a single file is of lower quality (e.g. 128kbps or VBR), we are not satisfied
                return False

        return True  # All files are 320 or FLAC
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error checking quality for album ID {album_id}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Quality verification error for ID {album_id}: {e}")
        return False

def should_skip_monitoring(config: Dict[str, Any], api_base: str, headers: Dict[str, str], album: Dict[str, Any]) -> bool:
    """
    Determine if an album should be skipped during monitoring based on quality filters.

    Args:
        config (Dict[str, Any]): Configuration dictionary
        api_base (str): Base URL for Lidarr API
        headers (Dict[str, str]): HTTP headers with API key
        album (Dict[str, Any]): Album data from Lidarr

    Returns:
        bool: True if album should be skipped during monitoring, False otherwise
    """
    # Check if quality filtering is enabled in config
    monitor_filters = config.get('monitor_quality_filters', {})
    exclude_qualities = monitor_filters.get('exclude_qualities', [])

    if not exclude_qualities:
        return False

    # If album doesn't have an ID, we can't check quality
    album_id = album.get('id')
    if not album_id:
        return False

    try:
        # Retrieve track files for this album
        res = requests.get(
            f"{api_base}/trackfile",
            params={"albumId": album_id},
            headers=headers,
            timeout=30
        )
        res.raise_for_status()
        files = res.json()

        if not files:
            return False

        # Get the exclude_all_files setting, default to False if not specified
        exclude_all_files = monitor_filters.get('exclude_all_files', False)

        if exclude_all_files:
            # Only skip if ALL files match the exclude criteria
            all_files_match = True
            for f in files:
                quality_name = f.get('quality', {}).get('quality', {}).get('name', '').upper()
                file_matches_criteria = any(exclude_quality.upper() in quality_name for exclude_quality in exclude_qualities)
                if not file_matches_criteria:
                    all_files_match = False
                    break
            return all_files_match
        else:
            # Skip if ANY file matches the exclude criteria
            for f in files:
                quality_name = f.get('quality', {}).get('quality', {}).get('name', '').upper()
                file_matches_criteria = any(exclude_quality.upper() in quality_name for exclude_quality in exclude_qualities)
                if file_matches_criteria:
                    return True

        return False  # No files matched exclusion criteria

    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error checking quality for album ID {album_id}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Quality verification error for ID {album_id}: {e}")
        return False

def process_album(api_base: str, headers: Dict[str, str], album: Dict[str, Any], dry_run: bool = False) -> None:
    """
    Process an album: enable monitoring if it's not already satisfactory.

    Args:
        api_base (str): Base URL for Lidarr API
        headers (Dict[str, str]): HTTP headers with API key
        album (Dict[str, Any]): Album data from Lidarr
        dry_run (bool): If True, simulate execution without making changes
    """
    album_title = album.get('title', 'Unknown Title')
    album_id = album.get('id')

    # Quality exclusion rule check
    if is_quality_satisfied(api_base, headers, album):
        logger.info(f"⏭️  Skipped: {album_title} is already complete in High Quality.")
        return

    # Otherwise, enable monitoring
    if dry_run:
        logger.info(f"🔍 [DRY-RUN] Would enable monitoring for: {album_title}")
        logger.info(f"🔎 [DRY-RUN] Would launch search for: {album_title}")
        return

    try:
        album['monitored'] = True
        response = requests.put(
            f"{api_base}/album",
            json=album,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        logger.info(f"✅ [Monitoring] Enabled for: {album_title}")

        # Launch search
        search_payload = {"name": "AlbumSearch", "albumIds": [album_id]}
        requests.post(
            f"{api_base}/command",
            json=search_payload,
            headers=headers,
            timeout=30
        )
        logger.info(f"🔎 [Search] Launched.")

        time.sleep(0.5)  # API protection
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error processing album {album_title}: {e}")
    except Exception as e:
        logger.error(f"Error processing album {album_title}: {e}")

def get_lidarr_artists_by_tag(config: Dict[str, Any], tag_name: str) -> List[str]:
    """
    Retrieve list of artists from Lidarr via tag.

    Args:
        config (Dict[str, Any]): Configuration dictionary
        tag_name (str): Name of the tag to filter artists by

    Returns:
        List[str]: List of artist names matching the tag
    """
    try:
        headers = {"X-Api-Key": config['lidarr']['api_key']}
        base_url = config['lidarr']['url']

        # Get all tags
        r = requests.get(
            f"{base_url}/api/v1/tag",
            headers=headers,
            timeout=30
        )
        r.raise_for_status()
        tags = r.json()

        # Find tag ID
        tag_id = next((t['id'] for t in tags if t['label'].lower() == tag_name.lower()), None)

        if tag_id is None:
            logger.error(f"Tag '{tag_name}' does not exist in Lidarr.")
            return []

        # Get all artists
        r = requests.get(
            f"{base_url}/api/v1/artist",
            headers=headers,
            timeout=30
        )
        r.raise_for_status()
        artists = r.json()

        # Filter artists by tag
        return [a['artistName'] for a in artists if tag_id in a.get('tags', [])]

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error retrieving artists by tag: {e}")
        return []
    except Exception as e:
        logger.error(f"Lidarr error: {e}")
        return []

def sync_plex_collection(config: Dict[str, Any], lidarr_names: List[str], collection_name: str, dry_run: bool = False) -> None:
    """
    Synchronize Plex collection with Lidarr artists.

    Args:
        config (Dict[str, Any]): Configuration dictionary
        lidarr_names (List[str]): List of artist names from Lidarr
        collection_name (str): Name of the Plex collection to manage
        dry_run (bool): If True, simulate execution without making changes
    """
    try:
        plex = PlexServer(config['plex']['url'], config['plex']['token'])
        music_lib = plex.library.section(config['plex']['library_name'])
    except Exception as e:
        logger.error(f"Plex connection error: {e}")
        sys.exit(1)

    try:
        all_plex_artists = music_lib.all()
        plex_artist_map = {artist.title.lower(): artist for artist in all_plex_artists}

        artists_to_collect = [plex_artist_map[n.lower()] for n in lidarr_names if n.lower() in plex_artist_map]

        collections = music_lib.collections(title=collection_name)

        if collections:
            collection = collections[0]
            logger.info(f"Updating collection: '{collection_name}'")

            current_collection_items = collection.items()
            current_set = set(item.ratingKey for item in current_collection_items)
            target_set = set(item.ratingKey for item in artists_to_collect)

            to_add = [a for a in artists_to_collect if a.ratingKey not in current_set]
            to_remove = [a for a in current_collection_items if a.ratingKey not in target_set]

            if dry_run:
                logger.info(f"🔍 [DRY-RUN] Would update collection: '{collection_name}'")
                logger.info(f"🔍 [DRY-RUN] Would add {len(to_add)} artists and remove {len(to_remove)} artists")
            else:
                if to_add:
                    collection.addItems(to_add)
                if to_remove:
                    collection.removeItems(to_remove)

                logger.info(f"Result: +{len(to_add)} / -{len(to_remove)} artists.")
        else:
            logger.info(f"Creating collection: '{collection_name}'")
            if dry_run:
                logger.info(f"🔍 [DRY-RUN] Would create collection: '{collection_name}' with {len(artists_to_collect)} artists")
            else:
                if artists_to_collect:
                    music_lib.createCollection(title=collection_name, items=artists_to_collect)
                    logger.info(f"Success: {len(artists_to_collect)} artists added.")
    except Exception as e:
        logger.error(f"Error syncing Plex collection: {e}")

def unmonitor_high_quality_albums(config: Dict[str, Any], dry_run: bool = False) -> None:
    """
    Disable monitoring for albums already in high quality (FLAC/320).

    Args:
        config (Dict[str, Any]): Configuration dictionary
        dry_run (bool): If True, simulate execution without making changes
    """
    url = config['lidarr']['url'].rstrip('/')
    api_key = config['lidarr']['api_key']
    headers = {'X-Api-Key': api_key}

    logger.info(f"--- Connecting to Lidarr at {url} ---")

    try:
        # Retrieve artists to avoid loading all albums at once (Error 500)
        artist_res = requests.get(
            f"{url}/api/v1/artist",
            headers=headers,
            timeout=30
        )
        artist_res.raise_for_status()
        artists = artist_res.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error connecting to Lidarr: {e}")
        return
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return

    total_artists = len(artists)
    logger.info(f"Analyzing {total_artists} artists...")
    count_updated = 0

    for i, artist in enumerate(artists, 1):
        artist_id = artist.get('id')
        artist_name = artist.get('artistName', 'Unknown Artist')
        logger.info(f"Progress: ({i}/{total_artists}) - Analyzing artist: {artist_name}")

        if not artist_id:
            continue

        # Retrieve artist's albums
        try:
            albums_response = requests.get(
                f"{url}/api/v1/album",
                params={'artistId': artist_id},
                headers=headers,
                timeout=30
            )
            albums_response.raise_for_status()
            albums = albums_response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error retrieving albums for artist {artist_name} (ID: {artist_id}): {e}")
            continue
        except Exception as e:
            logger.warning(f"Error retrieving albums for artist {artist_name} (ID: {artist_id}): {e}")
            continue

        for album in albums:
            # Safely check if album is a dict before accessing its keys
            if not isinstance(album, dict):
                logger.warning(f"Unexpected album data type: {type(album)}, skipping")
                continue

            # Additional safety check for album data
            try:
                # Verify album has required fields before using them
                if not album.get('id'):
                    logger.warning(f"Album missing ID field, skipping: {album}")
                    continue

                album_id = album.get('id')
                album_title = album.get('title', 'Unknown Album')

                # Skip if album is not monitored (already handled in calling function)
                if not album.get('monitored', False):
                    continue

            except Exception as e:
                logger.warning(f"Error processing album data: {e}, skipping album")
                continue

            # Check file quality
            try:
                files_res = requests.get(
                    f"{url}/api/v1/trackfile",
                    params={'albumId': album_id},
                    headers=headers,
                    timeout=30
                )

                if files_res.status_code != 200:
                    continue

                track_files = files_res.json()
                if not track_files:
                    continue

                should_unmonitor = False
                found_quality = ""

                for file in track_files:
                    quality = file.get('quality', {}).get('quality', {}).get('name', "").upper()
                    # Criteria: contains "FLAC" or "320"
                    if "FLAC" in quality or "320" in quality:
                        should_unmonitor = True
                        found_quality = quality
                        break

                if should_unmonitor:
                    if dry_run:
                        logger.info(f"🔍 [DRY-RUN] Would unmonitor: {artist_name} - {album_title} ({found_quality})")
                    else:
                        album['monitored'] = False
                        update = requests.put(
                            f"{url}/api/v1/album/{album_id}",
                            json=album,
                            headers=headers,
                            timeout=30
                        )

                        if update.status_code in [200, 202]:
                            logger.info(f"[UNMONITORED] {artist_name} - {album_title} ({found_quality})")
                            count_updated += 1

            except requests.exceptions.RequestException as e:
                logger.warning(f"Network error checking album quality {album_title}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error checking album quality {album_title}: {e}")
                continue

    logger.info(f"\nCompleted! {count_updated} albums updated.")

def sync_likes(config: Dict[str, Any], dry_run: bool = False) -> None:
    """
    Create a Plex playlist from liked Spotify tracks.

    Args:
        config (Dict[str, Any]): Configuration dictionary
        dry_run (bool): If True, simulate execution without making changes
    """
    try:
        # Spotify
        sp_config = config['spotify']
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=sp_config['client_id'],
            client_secret=sp_config['client_secret'],
            redirect_uri=sp_config['redirect_uri'],
            scope="user-library-read"
        ))

        # Plex
        p_config = config['plex']
        plex = PlexServer(p_config['url'], p_config['token'])
        music_library = plex.library.section(p_config['library_name'])
    except KeyError as e:
        logger.error(f"Missing key in YAML configuration: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        sys.exit(1)

    logger.info(f"🚀 Reading config: {CONFIG_FILE}")
    logger.info("📡 Retrieving liked tracks from Spotify...")

    try:
        results = sp.current_user_saved_tracks(limit=50)
        spotify_tracks = results['items']

        while results['next']:
            results = sp.next(results)
            spotify_tracks.extend(results['items'])

        logger.info(f"🎵 Found {len(spotify_tracks)} tracks. Searching in Plex...")

        plex_tracks = []

        for item in spotify_tracks:
            track = item['track']
            artist_name = track['artists'][0]['name']
            track_name = track['name']

            # Simple search in Plex
            try:
                search_results = music_library.searchTracks(title=track_name)

                for p_track in search_results:
                    if p_track.artist().title.lower() == artist_name.lower():
                        plex_tracks.append(p_track)
                        break
            except Exception as e:
                logger.warning(f"Error searching for track {track_name} by {artist_name}: {e}")
                continue

        # Update playlist
        if plex_tracks:
            pl_name = p_config.get('playlist_name', 'Spotify Likes')
            if dry_run:
                logger.info(f"🔍 [DRY-RUN] Would update playlist: '{pl_name}' with {len(plex_tracks)} tracks")
            else:
                try:
                    plex.playlist(pl_name).delete()
                except:
                    pass

                plex.createPlaylist(pl_name, items=plex_tracks)
                logger.info(f"✅ Playlist '{pl_name}' updated ({len(plex_tracks)} tracks).")
        else:
            logger.warning("⚠️ No matching tracks found in Plex.")

    except Exception as e:
        logger.error(f"Error syncing Spotify likes: {e}")

# ================= MAIN FUNCTIONS =================

def monitor_unmonitored(config: Dict[str, Any], dry_run: bool = False) -> None:
    """
    Main function to monitor unmonitored albums.

    Args:
        config (Dict[str, Any]): Configuration dictionary
        dry_run (bool): If True, simulate execution without making changes
    """
    url = config['lidarr']['url'].rstrip('/')
    api_key = config['lidarr']['api_key']
    api_base = f"{url}/api/v1"
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    try:
        logger.info(f"📡 Connecting to Lidarr: {url}")
        artists = requests.get(
            f"{api_base}/artist",
            headers=headers,
            timeout=30
        ).json()

        for artist in artists:
            logger.info(f"\n👤 Artist: {artist['artistName']}")
            albums = requests.get(
                f"{api_base}/album",
                params={"artistId": artist['id']},
                headers=headers,
                timeout=30
            ).json()

            # Only process UNMONITORED albums
            unmonitored = []
            for a in albums:
                # Safety check for malformed data
                if isinstance(a, dict):
                    if not a.get('monitored', False):
                        unmonitored.append(a)
                else:
                    logger.warning(f"Skipping non-dict album data: {type(a)}")
                    continue

            for album in unmonitored:
                # Check if album should be skipped based on quality filters
                if should_skip_monitoring(config, api_base, headers, album):
                    album_title = album.get('title', 'Unknown Title')
                    logger.info(f"⏭️  Skipped: {album_title} (quality filter)")
                    continue
                process_album(api_base, headers, album, dry_run)

            time.sleep(0.2)

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error in monitor_unmonitored: {e}")
    except Exception as e:
        logger.error(f"Critical error in monitor_unmonitored: {e}")

# ================= MAIN ENTRY POINT =================

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    import readline  # Import here to avoid issues in some environments

    # Ask for confirmation before exiting
    try:
        response = input('\nAre you sure you want to exit? (y/N): ').strip().lower()
        if response in ['y', 'yes']:
            logger.info('Exiting as requested.')
            sys.exit(0)
        else:
            logger.info('Continuing execution...')
            # Re-register the signal handler to allow for another interrupt
            signal.signal(signal.SIGINT, signal_handler)
    except (KeyboardInterrupt, EOFError):
        # If user presses Ctrl+C again during confirmation, exit anyway
        logger.info('Force exiting...')
        sys.exit(1)

def main():
    """Main entry point for the script."""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(
        description="Lidarr and Plex synchronization script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s monitor
  %(prog)s sync-tag "MyTag" "MyCollection"
  %(prog)s unmonitor
  %(prog)s sync-likes
        """
    )
    parser.add_argument('--dry-run', action='store_true', help='Simulate execution without making changes')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Subcommand monitor
    monitor_parser = subparsers.add_parser('monitor', help='Monitor unmonitored albums')

    # Subcommand sync-tag
    sync_tag_parser = subparsers.add_parser('sync-tag', help='Synchronize Lidarr artists with a Plex collection')
    sync_tag_parser.add_argument('tag', help='Lidarr tag name')
    sync_tag_parser.add_argument('collection', help='Plex collection name')

    # Subcommand unmonitor
    unmonitor_parser = subparsers.add_parser('unmonitor', help='Disable monitoring for high quality albums')

    # Subcommand sync-likes
    sync_likes_parser = subparsers.add_parser('sync-likes', help='Synchronize Spotify likes to a Plex playlist')

    args = parser.parse_args()

    config = load_config()

    if args.command == 'monitor':
        monitor_unmonitored(config, args.dry_run)
    elif args.command == 'sync-tag':
        lidarr_names = get_lidarr_artists_by_tag(config, args.tag)
        if lidarr_names:
            sync_plex_collection(config, lidarr_names, args.collection, args.dry_run)
        else:
            logger.info("No artists found with this tag.")
    elif args.command == 'unmonitor':
        unmonitor_high_quality_albums(config, args.dry_run)
    elif args.command == 'sync-likes':
        sync_likes(config, args.dry_run)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
