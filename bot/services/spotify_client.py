"""
Spotify client wrapper using spotipy
"""

import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import List, Dict, Optional, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import time

from bot.utils.config import load_config, get_redirect_uri
from bot.services.user_settings import UserSettings

logger = logging.getLogger(__name__)

class SpotifyClient:
    """Spotify API client wrapper"""
    
    def __init__(self, user_id: int = None):
        self.user_id = user_id
        self.user_settings = UserSettings()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._sp = None
    
    def _get_spotify_instance(self) -> Optional[spotipy.Spotify]:
        """Get Spotify instance with user credentials (token from DB only!)"""
        try:
            if self.user_id:
                # Get user-specific credentials
                credentials = self.user_settings.get_spotify_credentials(self.user_id)
                if credentials:
                    # Get stored tokens
                    conn = sqlite3.connect(self.user_settings.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT spotify_access_token, spotify_refresh_token, spotify_token_expires_at
                        FROM user_settings WHERE user_id = ?
                    ''', (self.user_id,))
                    result = cursor.fetchone()
                    conn.close()
                    if not result or not result[0]:
                        return None
                    access_token, refresh_token, expires_at = result
                    # Refresh if expired
                    if expires_at and expires_at < time.time():
                        sp_oauth = SpotifyOAuth(
                            client_id=credentials["client_id"],
                            client_secret=credentials["client_secret"],
                            redirect_uri=get_redirect_uri(),
                            scope="user-top-read user-read-recently-played playlist-modify-public user-read-private user-library-read",
                            open_browser=False
                        )
                        new_token_info = sp_oauth.refresh_access_token(refresh_token)
                        self.user_settings.save_spotify_tokens(
                            self.user_id,
                            new_token_info['access_token'],
                            new_token_info['refresh_token'],
                            new_token_info['expires_in']
                        )
                        access_token = new_token_info['access_token']
                    return spotipy.Spotify(auth=access_token)
            return None
        except Exception as e:
            logger.error(f"Error creating Spotify instance: {e}")
            return None
    
    @property
    def sp(self) -> Optional[spotipy.Spotify]:
        """Get Spotify instance (lazy loading)"""
        if self._sp is None:
            self._sp = self._get_spotify_instance()
        return self._sp
    
    def get_auth_url(self) -> Optional[str]:
        """Generate Spotify authorization URL for the user (old project style)"""
        try:
            if not self.user_id:
                return None
            credentials = self.user_settings.get_spotify_credentials(self.user_id)
            if not credentials:
                return None
            redirect_uri = get_redirect_uri()
            scope = (
                "user-top-read user-read-recently-played playlist-modify-public "
                "playlist-modify-private user-library-read"
            )
            sp_oauth = SpotifyOAuth(
                client_id=credentials["client_id"],
                client_secret=credentials["client_secret"],
                redirect_uri=redirect_uri,
                scope=scope,
                state=str(self.user_id),
                open_browser=False
            )
            return sp_oauth.get_authorize_url()
        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            return None
    
    def is_authorized(self) -> bool:
        """Check if user is authorized with Spotify"""
        try:
            if not self.user_id:
                return False
            
            # Check if user has valid tokens
            credentials = self.user_settings.get_spotify_credentials(self.user_id)
            if not credentials:
                return False
            
            # Get stored tokens
            conn = sqlite3.connect(self.user_settings.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT spotify_access_token, spotify_refresh_token, spotify_token_expires_at
                FROM user_settings WHERE user_id = ?
            ''', (self.user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result[0]:
                return False
            
            access_token, refresh_token, expires_at = result
            
            # Check if token is expired
            if expires_at and expires_at < time.time():
                # Try to refresh token
                try:
                    redirect_uri = get_redirect_uri()
                    scope = (
                        "user-top-read user-read-recently-played playlist-modify-public "
                        "playlist-modify-private user-library-read"
                    )
                    sp_oauth = SpotifyOAuth(
                        client_id=credentials["client_id"],
                        client_secret=credentials["client_secret"],
                        redirect_uri=redirect_uri,
                        scope=scope,
                        state=str(self.user_id),
                        open_browser=False
                    )
                    new_token_info = sp_oauth.refresh_access_token(refresh_token)
                    self.user_settings.save_spotify_tokens(
                        self.user_id,
                        new_token_info['access_token'],
                        new_token_info['refresh_token'],
                        new_token_info['expires_in']
                    )
                    access_token = new_token_info['access_token']
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    return False
            
            # Test token by making a simple API call
            try:
                test_sp = spotipy.Spotify(auth=access_token)
                user = test_sp.current_user()
                return user is not None
            except Exception as e:
                logger.error(f"Error testing token: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error checking authorization: {e}")
            return False
    
    async def get_top_tracks(self, user_id: int, limit: int = 15, time_range: str = "short_term") -> List[Dict]:
        """Get user's top tracks"""
        try:
            if not self.sp:
                return []
            
            # Check if user is authorized
            if not self.is_authorized():
                logger.warning(f"User {user_id} is not authorized with Spotify")
                return []
            
            loop = asyncio.get_event_loop()
            tracks = await loop.run_in_executor(
                self.executor,
                self.sp.current_user_top_tracks,
                limit,
                0,
                time_range
            )
            return tracks['items']
        except Exception as e:
            logger.error(f"Error fetching top tracks: {e}")
            return []
    
    async def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user data for analytics"""
        try:
            if not self.sp:
                return {}
            
            # Check if user is authorized
            if not self.is_authorized():
                logger.warning(f"User {user_id} is not authorized with Spotify")
                return {}
            
            loop = asyncio.get_event_loop()
            
            # Get top tracks
            top_tracks = await loop.run_in_executor(
                self.executor,
                self.sp.current_user_top_tracks,
                50,
                0,
                "short_term"
            )
            
            # Get recently played
            recent_tracks = await loop.run_in_executor(
                self.executor,
                self.sp.current_user_recently_played,
                50
            )
            
            # Get user profile
            profile = await loop.run_in_executor(
                self.executor,
                self.sp.current_user
            )
            
            return {
                'top_tracks': top_tracks['items'],
                'recent_tracks': recent_tracks['items'],
                'profile': profile
            }
        except Exception as e:
            logger.error(f"Error fetching user data: {e}")
            return {}
    
    async def search_track(self, track_name: str, artist_name: str = "") -> Optional[Dict]:
        """Search for a track on Spotify"""
        try:
            if not self.sp:
                return None
            
            query = f"{track_name} {artist_name}".strip()
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                self.sp.search,
                query,
                1,
                0,
                "track"
            )
            
            if results['tracks']['items']:
                return results['tracks']['items'][0]
            return None
        except Exception as e:
            logger.error(f"Error searching track: {e}")
            return None
    
    async def create_playlist(self, user_id: str, name: str, tracks: List[str]) -> Optional[str]:
        """Create a playlist with given tracks"""
        try:
            if not self.sp:
                return None
            
            # Check if user is authorized
            if not self.is_authorized():
                logger.warning(f"User {user_id} is not authorized with Spotify")
                return None
            
            loop = asyncio.get_event_loop()
            
            # Get current user's profile to get the correct user ID
            current_user = await loop.run_in_executor(
                self.executor,
                lambda: self.sp.current_user()
            )
            
            spotify_user_id = current_user['id']
            
            # Create playlist for the authenticated user
            playlist = await loop.run_in_executor(
                self.executor,
                lambda: self.sp.user_playlist_create(spotify_user_id, name, public=True)
            )
            
            # Add tracks to playlist in batches of 100 (Spotify API limit)
            if tracks:
                batch_size = 100
                for i in range(0, len(tracks), batch_size):
                    batch = tracks[i:i + batch_size]
                    await loop.run_in_executor(
                        self.executor,
                        lambda batch=batch: self.sp.playlist_add_items(playlist['id'], batch)
                    )
                    logger.info(f"Added batch {i//batch_size + 1} with {len(batch)} tracks to playlist")
            
            logger.info(f"Created playlist '{name}' with {len(tracks)} tracks")
            return playlist['id']
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return None
    
    async def get_track_features(self, track_id: str) -> Optional[Dict]:
        """Get audio features for a track"""
        try:
            if not self.sp:
                return None
            
            loop = asyncio.get_event_loop()
            features = await loop.run_in_executor(
                self.executor,
                self.sp.audio_features,
                [track_id]
            )
            return features[0] if features else None
        except Exception as e:
            logger.error(f"Error fetching track features: {e}")
            return None
    
    async def get_recently_played(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's recently played tracks"""
        try:
            if not self.sp:
                return []
            
            # Check if user is authorized
            if not self.is_authorized():
                logger.warning(f"User {user_id} is not authorized with Spotify")
                return []
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                self.sp.current_user_recently_played,
                limit
            )
            
            tracks = []
            for item in results['items']:
                track = item['track']
                tracks.append({
                    'name': track['name'],
                    'artists': track['artists'],
                    'id': track['id'],
                    'played_at': item['played_at']
                })
            
            return tracks
        except Exception as e:
            logger.error(f"Error fetching recently played tracks: {e}")
            return []
    
    async def get_user_liked_tracks(self, limit: int = 50) -> List[Dict]:
        """Get user's liked tracks"""
        try:
            if not self.sp:
                return []
            
            # Check if user is authorized
            if not self.is_authorized():
                logger.warning(f"User {self.user_id} is not authorized with Spotify")
                return []
            
            loop = asyncio.get_event_loop()
            tracks = await loop.run_in_executor(
                self.executor,
                self.sp.current_user_saved_tracks,
                limit,
                0
            )
            return tracks['items']
        except Exception as e:
            logger.error(f"Error fetching liked tracks: {e}")
            return []
    
    async def search_tracks(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for multiple tracks on Spotify"""
        try:
            if not self.sp:
                return []
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                self.sp.search,
                query,
                limit,
                0,
                "track"
            )
            
            return results['tracks']['items']
        except Exception as e:
            logger.error(f"Error searching tracks: {e}")
            return []
    
    def __del__(self):
        """Cleanup executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False) 