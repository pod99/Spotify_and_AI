"""
OpenRouter API client for AI music recommendations
"""

import aiohttp
import asyncio
import logging
import json
import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TrackRecommendation:
    """Track recommendation data structure"""
    title: str
    artist: str
    genre: str
    language: str
    reason: str
    source: str  # Which AI model generated this

class OpenRouterClient:
    """Client for OpenRouter API with multiple AI models"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        
        # Free models available on OpenRouter
        self.models = [
            "mistralai/mistral-7b-instruct",  # Free tier
            "meta-llama/llama-3.1-8b-instruct", # Free tier
            "anthropic/claude-3-haiku"  # Free tier (if available)
        ]
        
        # Headers for API requests
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://spotify-and-yandex-bot.com",
            "X-Title": "Spotify Yandex Bot"
        }
    
    def _build_prompt(self, track_count: int, genre: str, language: str, mood: str, activity: str = "general", liked_tracks: Set[str] = None) -> str:
        """Build the prompt for AI models"""
        # Request 30 more tracks than user wants for better filtering
        requested_count = track_count + 30
        
        # Build liked tracks section
        liked_tracks_section = ""
        if liked_tracks and len(liked_tracks) > 0:
            liked_list = list(liked_tracks)[:50]  # Take last 50 tracks
            liked_tracks_section = f"""
**Последние 50 залайканных треков пользователя:**
{chr(10).join([f"- {track}" for track in liked_list])}

**Важно:** НЕ включай эти треки в рекомендации, так как пользователь их уже знает и любит. Используй эту информацию для понимания музыкальных предпочтений пользователя.
"""
        
        prompt = f"""Ты — интеллектуальный музыкальный рекомендатор. Создай список из {requested_count} треков со следующими параметрами:

- Количество треков: {requested_count}
- Жанр: {genre}
- Язык исполнения: {language}
- Настроение: {mood}
- Сценарий прослушивания: {activity}

{liked_tracks_section}
Для каждого трека укажи:
1. **Название** — точное название песни в кавычках
2. **Исполнитель** — имя артиста или группы
3. **Жанр** — {genre} (или близкий)
4. **Язык исполнения** — {language}
5. **Краткое обоснование выбора** (1-2 предложения: почему соответствует настроению и активности)

Выдай результат в формате Markdown-списка:

1. "Название 1" — Исполнитель 1
Жанр: {genre}; Язык: {language}; Причина: подходит для настроения {mood} и активности {activity}.

2. "Название 2" — Исполнитель 2
Жанр: {genre}; Язык: {language}; Причина: [обоснование].

И так далее для всех {requested_count} треков. Используй только реальные существующие песни и исполнителей."""
        
        return prompt
    
    async def _call_model(self, model: str, prompt: str) -> Optional[str]:
        """Call a specific AI model via OpenRouter API"""
        try:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        content = data['choices'][0]['message']['content']
                        logger.info(f"Successfully called model {model}")
                        return content
                    else:
                        error_text = await response.text()
                        logger.error(f"Error calling model {model}: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Exception calling model {model}: {e}")
            return None
    
    def _parse_recommendations(self, content: str, source: str) -> List[TrackRecommendation]:
        """Parse AI response and extract track recommendations"""
        recommendations = []
        
        # Pattern to match numbered list items
        pattern = r'(\d+)\.\s*"([^"]+)"\s*—\s*([^\n]+)\nЖанр:\s*([^;]+);\s*Язык:\s*([^;]+);\s*Причина:\s*([^\n]+)'
        
        matches = re.findall(pattern, content, re.MULTILINE)
        
        for match in matches:
            try:
                number, title, artist, genre, language, reason = match
                
                # Clean up the data
                title = title.strip()
                artist = artist.strip()
                genre = genre.strip()
                language = language.strip()
                reason = reason.strip()
                
                # Create recommendation object
                rec = TrackRecommendation(
                    title=title,
                    artist=artist,
                    genre=genre,
                    language=language,
                    reason=reason,
                    source=source
                )
                
                recommendations.append(rec)
                
            except Exception as e:
                logger.warning(f"Failed to parse recommendation: {e}")
                continue
        
        logger.info(f"Parsed {len(recommendations)} recommendations from {source}")
        return recommendations
    
    async def get_recommendations(self, track_count: int, genre: str, language: str, mood: str, 
                                activity: str = "general", liked_tracks: Set[str] = None) -> List[TrackRecommendation]:
        """Get recommendations from multiple AI models and combine them"""
        
        if liked_tracks is None:
            liked_tracks = set()
        
        logger.info(f"Getting AI recommendations: {track_count} tracks, genre={genre}, language={language}, mood={mood}")
        
        # Build the prompt
        prompt = self._build_prompt(track_count, genre, language, mood, activity, liked_tracks)
        
        # Call all models concurrently
        tasks = []
        for model in self.models:
            task = self._call_model(model, prompt)
            tasks.append(task)
        
        # Wait for all responses
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Parse all recommendations
        all_recommendations = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"Model {self.models[i]} failed: {response}")
                continue
                
            if response:
                recommendations = self._parse_recommendations(response, self.models[i])
                all_recommendations.extend(recommendations)
        
        logger.info(f"Total recommendations from all models: {len(all_recommendations)}")
        
        # Remove duplicates based on title + artist
        unique_recommendations = self._remove_duplicates(all_recommendations)
        logger.info(f"After removing duplicates: {len(unique_recommendations)}")
        
        # Remove already liked tracks
        filtered_recommendations = self._filter_liked_tracks(unique_recommendations, liked_tracks)
        logger.info(f"After filtering liked tracks: {len(filtered_recommendations)}")
        
        # Return requested number of tracks
        final_recommendations = filtered_recommendations[:track_count]
        logger.info(f"Final recommendations: {len(final_recommendations)}")
        
        return final_recommendations
    
    def _remove_duplicates(self, recommendations: List[TrackRecommendation]) -> List[TrackRecommendation]:
        """Remove duplicate recommendations based on title + artist"""
        seen = set()
        unique_recommendations = []
        
        for rec in recommendations:
            # Create a key from title and artist (case insensitive)
            key = f"{rec.title.lower().strip()} - {rec.artist.lower().strip()}"
            
            if key not in seen:
                seen.add(key)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _filter_liked_tracks(self, recommendations: List[TrackRecommendation], liked_tracks: Set[str]) -> List[TrackRecommendation]:
        """Filter out tracks that user has already liked"""
        if not liked_tracks:
            return recommendations
        
        filtered = []
        
        for rec in recommendations:
            # Create search keys for the track
            title_artist = f"{rec.title.lower().strip()} - {rec.artist.lower().strip()}"
            artist_title = f"{rec.artist.lower().strip()} - {rec.title.lower().strip()}"
            
            # Check if this track is in liked tracks
            is_liked = False
            for liked_track in liked_tracks:
                liked_lower = liked_track.lower().strip()
                if (title_artist in liked_lower or 
                    artist_title in liked_lower or
                    rec.title.lower().strip() in liked_lower or
                    rec.artist.lower().strip() in liked_lower):
                    is_liked = True
                    break
            
            if not is_liked:
                filtered.append(rec)
        
        return filtered
    
    def format_recommendations_for_display(self, recommendations: List[TrackRecommendation]) -> str:
        """Format recommendations for Telegram display"""
        if not recommendations:
            return "❌ Не удалось получить рекомендации. Попробуйте другие параметры."
        
        result = f"🎵 AI рекомендует {len(recommendations)} треков:\n\n"
        
        for i, rec in enumerate(recommendations, 1):
            result += f"{i}. \"{rec.title}\" — {rec.artist}\n"
            result += f"Жанр: {rec.genre}; Язык: {rec.language}\n"
            result += f"💡 {rec.reason}\n\n"
        
        return result

    def get_genres(self):
        """Get available genres for selection"""
        genres = {
            'pop': '🎵 Pop',
            'rock': '🤘 Rock', 
            'electronic': '⚡ Electronic',
            'jazz': '🎷 Jazz',
            'classical': '🎼 Classical',
            'folk': '🪕 Folk',
            'hip-hop': '🎤 Hip-Hop',
            'country': '🤠 Country',
            'indie': '🎸 Indie',
            'alternative': '🎭 Alternative',
            'dance': '💃 Dance',
            'metal': '🔥 Metal',
            'r&b': '🎹 R&B',
            'reggae': '🌴 Reggae',
            'blues': '🎸 Blues',
            'punk': '⚡ Punk',
            'soul': '💙 Soul',
            'funk': '🎺 Funk',
            'disco': '🕺 Disco',
            'ambient': '🌊 Ambient'
        }
        logger.info(f"Available genres: {list(genres.keys())}")
        return genres

    def get_languages(self):
        """Get available languages for selection"""
        languages = {
            'english': '🇺🇸 English',
            'russian': '🇷🇺 Russian',
            'spanish': '🇪🇸 Spanish',
            'french': '🇫🇷 French',
            'german': '🇩🇪 German',
            'portuguese': '🇵🇹 Portuguese',
            'italian': '🇮🇹 Italian',
            'korean': '🇰🇷 Korean',
            'japanese': '🇯🇵 Japanese',
            'chinese': '🇨🇳 Chinese',
            'arabic': '🇸🇦 Arabic',
            'hindi': '🇮🇳 Hindi',
            'instrumental': '🎼 Instrumental'
        }
        logger.info(f"Available languages: {list(languages.keys())}")
        return languages

    def get_moods(self):
        """Get available moods for selection"""
        moods = {
            'happy': '😊 Happy',
            'sad': '😢 Sad',
            'energetic': '⚡ Energetic',
            'calm': '😌 Calm',
            'romantic': '💕 Romantic',
            'uplifting': '🌟 Uplifting',
            'melancholic': '🌧️ Melancholic',
            'intense': '🔥 Intense',
            'mysterious': '🔮 Mysterious',
            'epic': '⚔️ Epic',
            'dark': '🖤 Dark',
            'playful': '🎈 Playful',
            'chill': '😎 Chill',
            'relaxed': '🧘 Relaxed',
            'nostalgic': '📷 Nostalgic',
            'aggressive': '💥 Aggressive',
            'peaceful': '🕊️ Peaceful',
            'dramatic': '🎭 Dramatic',
            'funky': '🎺 Funky',
            'groovy': '🕺 Groovy'
        }
        logger.info(f"Available moods: {list(moods.keys())}")
        return moods 