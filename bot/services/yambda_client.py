"""
Yambda client adapter with local mock data
"""

import logging
from typing import List, Dict, Optional, Literal
import asyncio
from concurrent.futures import ThreadPoolExecutor
import random
from datasets import load_dataset
import requests

logger = logging.getLogger(__name__)

class YambdaClient:
    """Yambda recommendations via HuggingFace API - working with play events"""
    API_URL = "https://datasets-server.huggingface.co/rows"
    DATASET = "yandex/yambda"
    CONFIG = "flat-500m"  # Попробуем другой config
    SPLIT = "train"
    BATCH_SIZE = 100  # Уменьшим размер батча

    def __init__(self):
        self.rows = []
        self.track_info_cache = {}  # Кэш для информации о треках
        self.is_loaded = False
        self.languages = {
            'russian': 'Русский',
            'english': 'English', 
            'spanish': 'Español',
            'french': 'Français',
            'german': 'Deutsch',
            'italian': 'Italiano',
            'portuguese': 'Português',
            'japanese': '日本語',
            'korean': '한국어',
            'chinese': '中文',
            'other': 'Другой'
        }
        
        self.genres = {
            'pop': 'Pop',
            'rock': 'Rock',
            'hip-hop': 'Hip-Hop',
            'electronic': 'Electronic',
            'jazz': 'Jazz',
            'classical': 'Classical',
            'country': 'Country',
            'r&b': 'R&B',
            'indie': 'Indie',
            'folk': 'Folk',
            'metal': 'Metal',
            'punk': 'Punk',
            'reggae': 'Reggae',
            'blues': 'Blues',
            'soul': 'Soul',
            'funk': 'Funk',
            'disco': 'Disco',
            'house': 'House',
            'techno': 'Techno',
            'dubstep': 'Dubstep',
            'trap': 'Trap',
            'drum-and-bass': 'Drum & Bass',
            'ambient': 'Ambient',
            'lofi': 'Lo-Fi',
            'synthwave': 'Synthwave',
            'other': 'Другой'
        }
        
        self.moods = {
            'happy': 'Весёлый',
            'sad': 'Грустный',
            'energetic': 'Энергичный',
            'calm': 'Спокойный',
            'romantic': 'Романтичный',
            'melancholic': 'Меланхоличный',
            'uplifting': 'Вдохновляющий',
            'dark': 'Тёмный',
            'playful': 'Игривый',
            'intense': 'Интенсивный',
            'relaxed': 'Расслабленный',
            'mysterious': 'Загадочный',
            'nostalgic': 'Ностальгичный',
            'epic': 'Эпичный',
            'chill': 'Расслабляющий'
        }

        logger.info("YambdaClient initialized")

    async def load_dataset(self):
        """Load Yambda dataset via HuggingFace API"""
        try:
            logger.info(f"Loading Yambda dataset via API: {self.DATASET}/{self.CONFIG}")
            
            # Загружаем несколько батчей для получения больше данных
            all_rows = []
            for offset in range(0, 1000, self.BATCH_SIZE):  # Уменьшим общее количество
                params = {
                    "dataset": self.DATASET,
                    "config": self.CONFIG,
                    "split": self.SPLIT,
                    "offset": offset,
                    "length": self.BATCH_SIZE
                }
                logger.info(f"Loading batch with offset {offset}")
                
                resp = requests.get(self.API_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                
                batch_rows = [row['row'] for row in data.get('rows', [])]
                all_rows.extend(batch_rows)
                
                if len(batch_rows) < self.BATCH_SIZE:
                    break  # Достигли конца данных
                
                # Ограничим количество батчей
                if len(all_rows) >= 500:
                    break
            
            self.rows = all_rows
            self.is_loaded = True if self.rows else False
            
            logger.info(f"Yambda dataset loaded: {len(self.rows)} rows, is_loaded: {self.is_loaded}")
            if self.rows:
                logger.info(f"Sample row keys: {list(self.rows[0].keys())}")
                logger.info(f"Sample row: {self.rows[0]}")
                
                # Анализируем данные
                self._analyze_data_structure()
            
            return self.is_loaded
        except Exception as e:
            logger.error(f"Yambda API load error: {e}")
            # Попробуем другой config
            if self.CONFIG == "flat-500m":
                logger.info("Trying flat-50m config...")
                self.CONFIG = "flat-50m"
                return await self.load_dataset()
            elif self.CONFIG == "flat-50m":
                logger.info("Trying flat-5b config...")
                self.CONFIG = "flat-5b"
                return await self.load_dataset()
            else:
                logger.error("All configs failed, cannot load Yambda data")
                self.rows = []
                self.is_loaded = False
                return False

    def _analyze_data_structure(self):
        """Analyze the structure of loaded data"""
        if not self.rows:
            return
            
        # Анализируем уникальные item_id
        unique_items = set()
        event_types = set()
        users = set()
        
        for row in self.rows:
            unique_items.add(row.get('item_id'))
            event_types.add(row.get('event_type'))
            users.add(row.get('uid'))
        
        logger.info(f"Found {len(unique_items)} unique tracks")
        logger.info(f"Event types: {list(event_types)}")
        logger.info(f"Users: {len(users)}")
        
        # Группируем события по трекам
        track_events = {}
        for row in self.rows:
            item_id = row.get('item_id')
            if item_id not in track_events:
                track_events[item_id] = []
            track_events[item_id].append(row)
        
        # Создаем информацию о треках на основе событий
        self._build_track_info_from_events(track_events)

    def _build_track_info_from_events(self, track_events: Dict):
        """Build track information from play events"""
        logger.info("Building track info from play events...")
        
        for item_id, events in track_events.items():
            if len(events) == 0:
                continue
                
            # Берем первое событие как основу
            first_event = events[0]
            
            # Вычисляем популярность на основе количества событий
            popularity = min(100, len(events) * 10)  # Чем больше событий, тем популярнее
            
            # Определяем жанр на основе паттернов прослушивания
            genre = self._determine_genre_from_events(events)
            
            # Определяем язык на основе пользователей
            language = self._determine_language_from_events(events)
            
            # Определяем настроение на основе паттернов
            mood = self._determine_mood_from_events(events)
            
            # Безопасно вычисляем средние значения с обработкой None
            play_ratios = [e.get('played_ratio_pct', 0) or 0 for e in events]
            track_lengths = [e.get('track_length_seconds', 0) or 0 for e in events]
            
            avg_play_ratio = sum(play_ratios) / len(events) if events else 0
            avg_length = sum(track_lengths) / len(events) if events else 0
            
            # Создаем информацию о треке
            track_info = {
                'title': f"Track {item_id}",
                'artist': f"Artist {item_id}",
                'genre': genre,
                'language': language,
                'mood': mood,
                'year': 2020,  # Примерный год
                'popularity': popularity,
                'item_id': item_id,
                'play_count': len(events),
                'avg_play_ratio': avg_play_ratio,
                'avg_length': avg_length
            }
            
            self.track_info_cache[item_id] = track_info
        
        logger.info(f"Built track info for {len(self.track_info_cache)} tracks")

    def _determine_genre_from_events(self, events: List[Dict]) -> str:
        """Determine genre based on play patterns"""
        # Анализируем паттерны прослушивания для определения жанра
        total_plays = len(events)
        
        # Безопасно вычисляем средние значения с обработкой None
        play_ratios = [e.get('played_ratio_pct', 0) or 0 for e in events]
        track_lengths = [e.get('track_length_seconds', 0) or 0 for e in events]
        
        avg_play_ratio = sum(play_ratios) / total_plays if total_plays > 0 else 0
        avg_length = sum(track_lengths) / total_plays if total_plays > 0 else 0
        
        # Простая эвристика для определения жанра
        if avg_length > 300:  # Длинные треки
            return random.choice(['classical', 'jazz', 'progressive-rock'])
        elif avg_play_ratio > 80:  # Высокий процент прослушивания
            return random.choice(['pop', 'rock', 'electronic'])
        elif total_plays > 50:  # Много прослушиваний
            return random.choice(['pop', 'hip-hop', 'dance'])
        else:
            return random.choice(['indie', 'alternative', 'folk'])

    def _determine_language_from_events(self, events: List[Dict]) -> str:
        """Determine language based on user patterns"""
        # Анализируем пользователей для определения языка
        users = [e.get('uid', 0) or 0 for e in events]
        unique_users = len(set(users))
        
        # Простая эвристика на основе количества уникальных пользователей
        if unique_users > 100:
            return 'english'  # Популярные треки обычно на английском
        elif unique_users > 50:
            return random.choice(['english', 'russian', 'spanish'])
        else:
            return random.choice(['russian', 'french', 'german'])

    def _determine_mood_from_events(self, events: List[Dict]) -> str:
        """Determine mood based on play patterns"""
        # Анализируем паттерны для определения настроения
        # Безопасно вычисляем средние значения с обработкой None
        play_ratios = [e.get('played_ratio_pct', 0) or 0 for e in events]
        avg_play_ratio = sum(play_ratios) / len(events) if events else 0
        total_plays = len(events)
        
        if avg_play_ratio > 90:
            return random.choice(['happy', 'energetic', 'uplifting'])
        elif avg_play_ratio > 70:
            return random.choice(['calm', 'romantic', 'chill'])
        elif total_plays > 30:
            return random.choice(['intense', 'mysterious', 'epic'])
        else:
            return random.choice(['melancholic', 'sad', 'nostalgic'])

    async def get_recommendations(self, track_count=15, genre=None, mood=None, language=None, custom_genre=None, custom_language=None):
        logger.info(f"Getting recommendations: track_count={track_count}, genre={genre}, mood={mood}, language={language}, custom_genre={custom_genre}, custom_language=None")
        
        if not self.is_loaded:
            logger.info("Dataset not loaded, loading now...")
            await self.load_dataset()
        
        if not self.track_info_cache:
            logger.error("No track info available")
            return []
        
        # Фильтруем треки по критериям
        filtered_tracks = []
        for item_id, track_info in self.track_info_cache.items():
            # Применяем фильтры
            if genre and genre.lower() not in track_info['genre'].lower():
                continue
            if custom_genre and custom_genre.lower() not in track_info['genre'].lower():
                continue
            if language and language.lower() not in track_info['language'].lower():
                continue
            if custom_language and custom_language.lower() not in track_info['language'].lower():
                continue
            if mood and mood.lower() not in track_info['mood'].lower():
                continue
            
            filtered_tracks.append(track_info)
        
        # Сортируем по популярности и возвращаем нужное количество
        filtered_tracks.sort(key=lambda x: x['popularity'], reverse=True)
        
        logger.info(f"Found {len(filtered_tracks)} recommendations")
        return filtered_tracks[:track_count]

    def get_genres(self):
        """Get available genres from track cache"""
        genres = set()
        for track_info in self.track_info_cache.values():
            genres.add(track_info['genre'])
        
        if not genres:
            genres = {'pop', 'rock', 'electronic', 'jazz', 'classical', 'folk', 'hip-hop', 'country', 'indie', 'alternative', 'dance', 'metal'}
        
        genre_dict = {genre: genre.capitalize() for genre in genres}
        logger.info(f"Available genres: {list(genre_dict.keys())}")
        return genre_dict

    def get_languages(self):
        """Get available languages from track cache"""
        languages = set()
        for track_info in self.track_info_cache.values():
            languages.add(track_info['language'])
        
        if not languages:
            languages = {'english', 'russian', 'spanish', 'french', 'german', 'portuguese', 'korean'}
        
        language_dict = {lang: lang.capitalize() for lang in languages}
        logger.info(f"Available languages: {list(language_dict.keys())}")
        return language_dict

    def get_moods(self):
        """Get available moods from track cache"""
        moods = set()
        for track_info in self.track_info_cache.values():
            moods.add(track_info['mood'])
        
        if not moods:
            moods = {'happy', 'sad', 'energetic', 'calm', 'romantic', 'uplifting', 'melancholic', 'intense', 'mysterious', 'epic', 'dark', 'playful', 'chill', 'relaxed', 'nostalgic'}
        
        mood_dict = {mood: mood.capitalize() for mood in moods}
        logger.info(f"Available moods: {list(mood_dict.keys())}")
        return mood_dict

    async def search_tracks(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for tracks by query in track cache"""
        try:
            if not self.track_info_cache:
                await self.load_dataset()
            
            results = []
            query_lower = query.lower()
            
            for track_info in self.track_info_cache.values():
                if (query_lower in track_info['title'].lower() or 
                    query_lower in track_info['artist'].lower() or
                    query_lower in track_info['genre'].lower()):
                    results.append(track_info)
                    
                if len(results) >= limit:
                    break
                    
            return results
            
        except Exception as e:
            logger.error(f"Error searching tracks: {e}")
            return []
    
    async def filter_spotify_tracks(self, recommendations: List[Dict], spotify_client) -> List[Dict]:
        """Filter recommendations to only include tracks available on Spotify"""
        try:
            filtered_recs = []
            
            for rec in recommendations:
                # Try to find the track on Spotify
                try:
                    # Search for the track on Spotify
                    search_query = f"{rec.get('title', '')} {rec.get('artist', '')}"
                    spotify_tracks = await spotify_client.search_tracks(search_query, limit=1)
                    
                    if spotify_tracks:
                        track = spotify_tracks[0]
                        # Add Spotify data to recommendation
                        rec['spotify_id'] = track['id']
                        rec['spotify_uri'] = f"spotify:track:{track['id']}"
                        rec['spotify_name'] = track['name']
                        rec['spotify_artist'] = track['artists'][0]['name'] if track['artists'] else rec.get('artist', '')
                        filtered_recs.append(rec)
                    else:
                        # If not found on Spotify, skip this track
                        logger.debug(f"Track not found on Spotify: {search_query}")
                        
                except Exception as e:
                    logger.debug(f"Error searching track on Spotify: {e}")
                    continue
            
            logger.info(f"Filtered {len(filtered_recs)} tracks for Spotify out of {len(recommendations)} recommendations")
            return filtered_recs
            
        except Exception as e:
            logger.error(f"Error filtering Spotify tracks: {e}")
            return []
    
    async def store_user_feedback(self, user_id: int, track_id: str, feedback: str):
        """Store user feedback for future model retraining"""
        try:
            # In a real implementation, this would store to a database
            # For now, we'll just log it
            logger.info(f"User {user_id} gave {feedback} feedback for track {track_id}")
            
        except Exception as e:
            logger.error(f"Error storing user feedback: {e}")
    
    def __del__(self):
        """Cleanup executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False) 