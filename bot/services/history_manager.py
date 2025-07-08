"""
History manager for reading/writing play history and computing top counts
"""

import json
import logging
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
from collections import Counter

logger = logging.getLogger(__name__)

class HistoryManager:
    """Manages user play history and analytics"""
    
    def __init__(self, db_path: str = "music_history.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tracks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spotify_id TEXT UNIQUE,
                    track_name TEXT NOT NULL,
                    artist_name TEXT NOT NULL,
                    album_name TEXT,
                    genre TEXT,
                    duration_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create play_history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS play_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    track_id INTEGER NOT NULL,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    play_count INTEGER DEFAULT 1,
                    FOREIGN KEY (track_id) REFERENCES tracks (id)
                )
            ''')
            
            # Create user_feedback table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    track_id TEXT NOT NULL,
                    feedback TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    async def add_track_play(self, user_id: int, track_data: Dict):
        """Add a track play to history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert or update track
            cursor.execute('''
                INSERT OR REPLACE INTO tracks 
                (spotify_id, track_name, artist_name, album_name, genre, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                track_data.get('id'),
                track_data.get('name'),
                ', '.join([artist['name'] for artist in track_data.get('artists', [])]),
                track_data.get('album', {}).get('name'),
                track_data.get('genre'),
                track_data.get('duration_ms')
            ))
            
            track_id = cursor.lastrowid
            
            # Add play history
            cursor.execute('''
                INSERT INTO play_history (user_id, track_id, played_at)
                VALUES (?, ?, ?)
            ''', (user_id, track_id, datetime.now()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error adding track play: {e}")
    
    async def get_top_tracks(self, user_id: int, limit: int = 15, days: int = 30) -> List[Dict]:
        """Get user's top tracks with play counts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get top tracks from last N days
            since_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    t.track_name,
                    t.artist_name,
                    t.album_name,
                    t.genre,
                    COUNT(ph.id) as play_count
                FROM play_history ph
                JOIN tracks t ON ph.track_id = t.id
                WHERE ph.user_id = ? AND ph.played_at >= ?
                GROUP BY t.id
                ORDER BY play_count DESC
                LIMIT ?
            ''', (user_id, since_date, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            tracks = []
            for row in results:
                tracks.append({
                    'track_name': row[0],
                    'artist_name': row[1],
                    'album_name': row[2],
                    'genre': row[3],
                    'play_count': row[4]
                })
            
            return tracks
            
        except Exception as e:
            logger.error(f"Error getting top tracks: {e}")
            return []
    
    async def get_activity_by_hour(self, user_id: int, days: int = 30) -> Dict[int, int]:
        """Get listening activity by hour of day"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT strftime('%H', ph.played_at) as hour, COUNT(*) as count
                FROM play_history ph
                WHERE ph.user_id = ? AND ph.played_at >= ?
                GROUP BY hour
                ORDER BY hour
            ''', (user_id, since_date))
            
            results = cursor.fetchall()
            conn.close()
            
            activity = {int(hour): count for hour, count in results}
            
            # Fill missing hours with 0
            for hour in range(24):
                if hour not in activity:
                    activity[hour] = 0
            
            return activity
            
        except Exception as e:
            logger.error(f"Error getting activity by hour: {e}")
            return {}
    
    async def get_activity_by_day(self, user_id: int, days: int = 30) -> Dict[str, int]:
        """Get listening activity by day of week"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT strftime('%w', ph.played_at) as day, COUNT(*) as count
                FROM play_history ph
                WHERE ph.user_id = ? AND ph.played_at >= ?
                GROUP BY day
                ORDER BY day
            ''', (user_id, since_date))
            
            results = cursor.fetchall()
            conn.close()
            
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            activity = {day_names[int(day)]: count for day, count in results}
            
            # Fill missing days with 0
            for day in day_names:
                if day not in activity:
                    activity[day] = 0
            
            return activity
            
        except Exception as e:
            logger.error(f"Error getting activity by day: {e}")
            return {}
    
    async def get_top_genres(self, user_id: int, limit: int = 10, days: int = 30) -> List[Dict]:
        """Get user's top genres"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    t.genre,
                    COUNT(ph.id) as play_count
                FROM play_history ph
                JOIN tracks t ON ph.track_id = t.id
                WHERE ph.user_id = ? AND ph.played_at >= ? AND t.genre IS NOT NULL
                GROUP BY t.genre
                ORDER BY play_count DESC
                LIMIT ?
            ''', (user_id, since_date, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            genres = []
            for row in results:
                genres.append({
                    'genre': row[0],
                    'play_count': row[1]
                })
            
            return genres
            
        except Exception as e:
            logger.error(f"Error getting top genres: {e}")
            return []
    
    async def get_top_artists(self, user_id: int, limit: int = 10, days: int = 30) -> List[Dict]:
        """Get user's top artists"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    t.artist_name,
                    COUNT(ph.id) as play_count
                FROM play_history ph
                JOIN tracks t ON ph.track_id = t.id
                WHERE ph.user_id = ? AND ph.played_at >= ?
                GROUP BY t.artist_name
                ORDER BY play_count DESC
                LIMIT ?
            ''', (user_id, since_date, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            artists = []
            for row in results:
                artists.append({
                    'artist_name': row[0],
                    'play_count': row[1]
                })
            
            return artists
            
        except Exception as e:
            logger.error(f"Error getting top artists: {e}")
            return []
    
    async def store_user_feedback(self, user_id: int, track_id: str, feedback: str):
        """Store user feedback for tracks"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_feedback (user_id, track_id, feedback)
                VALUES (?, ?, ?)
            ''', (user_id, track_id, feedback))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing user feedback: {e}") 