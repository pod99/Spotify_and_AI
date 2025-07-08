"""
User settings management service
"""

import json
import logging
import sqlite3
from typing import Dict, Optional
import os
import time

logger = logging.getLogger(__name__)

class UserSettings:
    """Manages user-specific settings and credentials"""
    
    def __init__(self, db_path: str = "user_settings.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for user settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create user_settings table with token fields
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    spotify_client_id TEXT,
                    spotify_client_secret TEXT,
                    spotify_access_token TEXT,
                    spotify_refresh_token TEXT,
                    spotify_token_expires_at INTEGER,
                    is_setup_complete BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing user settings database: {e}")
    
    def is_user_setup_complete(self, user_id: int) -> bool:
        """Check if user has completed initial setup"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT is_setup_complete FROM user_settings 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else False
            
        except Exception as e:
            logger.error(f"Error checking user setup status: {e}")
            return False
    
    def save_spotify_credentials(self, user_id: int, client_id: str, client_secret: str) -> bool:
        """Save user's Spotify credentials"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_settings 
                (user_id, spotify_client_id, spotify_client_secret, is_setup_complete, updated_at)
                VALUES (?, ?, ?, TRUE, CURRENT_TIMESTAMP)
            ''', (user_id, client_id, client_secret))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving Spotify credentials: {e}")
            return False
    
    def get_spotify_credentials(self, user_id: int) -> Optional[Dict[str, str]]:
        """Get user's Spotify credentials"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT spotify_client_id, spotify_client_secret 
                FROM user_settings 
                WHERE user_id = ? AND is_setup_complete = TRUE
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'client_id': result[0],
                    'client_secret': result[1]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting Spotify credentials: {e}")
            return None
    
    def delete_user_settings(self, user_id: int) -> bool:
        """Delete user's settings (for reset)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM user_settings WHERE user_id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user settings: {e}")
            return False
    
    def save_spotify_tokens(self, user_id: int, access_token: str, refresh_token: str, expires_in: int) -> bool:
        """Save user's Spotify access and refresh tokens"""
        try:
            expires_at = int(time.time()) + int(expires_in)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_settings
                SET spotify_access_token = ?, spotify_refresh_token = ?, spotify_token_expires_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (access_token, refresh_token, expires_at, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving Spotify tokens: {e}")
            return False 