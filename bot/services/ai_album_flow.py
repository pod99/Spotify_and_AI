"""
AI Album conversation flow and playlist creation
"""

import logging
from typing import Dict, List, Optional
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.services.spotify_client import SpotifyClient
from bot.services.openrouter_client import OpenRouterClient
from bot.services.history_manager import HistoryManager
from bot.menus import get_back_to_main_menu
from bot.utils.config import get_config_value

logger = logging.getLogger(__name__)

class AIAlbumState(Enum):
    """AI Album conversation states"""
    IDLE = "idle"
    ASKING_TRACK_COUNT = "asking_track_count"
    ASKING_GENRE = "asking_genre"
    ASKING_LANGUAGE = "asking_language"
    ASKING_MOOD = "asking_mood"
    ASKING_ACTIVITY = "asking_activity"
    ASKING_PLAYLIST_NAME = "asking_playlist_name"
    CREATING_PLAYLIST = "creating_playlist"

class AIAlbumFlow:
    """Manages AI Album conversation flow"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.state = AIAlbumState.IDLE
        self.track_count = None
        self.genre = None
        self.custom_genre = None
        self.language = None
        self.custom_language = None
        self.mood = None
        self.activity = None
        self.playlist_name = None
        
        # Initialize services
        self.spotify_client = SpotifyClient(user_id)
        
        # Initialize OpenRouter client
        api_key = get_config_value('OPENROUTER_API_KEY')
        if api_key:
            self.openrouter_client = OpenRouterClient(api_key)
        else:
            self.openrouter_client = None
            logger.warning("OpenRouter API key not found")
        
        self.history_manager = HistoryManager()
    
    async def start_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the AI Album conversation"""
        self.state = AIAlbumState.ASKING_TRACK_COUNT
        
        welcome_message = (
            "🤖 Welcome to AI Album Creator!\n\n"
            "I'll help you create a personalized playlist using AI recommendations.\n\n"
            "How many tracks would you like in your playlist?"
        )
        
        # Create inline keyboard for track count selection
        keyboard = [
            [
                InlineKeyboardButton("🎵 15", callback_data="ai_album_track_count_15"),
                InlineKeyboardButton("🎵 25", callback_data="ai_album_track_count_25"),
                InlineKeyboardButton("🎵 40", callback_data="ai_album_track_count_40")
            ],
            [
                InlineKeyboardButton("🎵 60", callback_data="ai_album_track_count_60"),
                InlineKeyboardButton("🎵 100", callback_data="ai_album_track_count_100"),
                InlineKeyboardButton("🎵 150", callback_data="ai_album_track_count_150")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Check if this is a callback query or regular message
        if update.callback_query:
            await update.callback_query.edit_message_text(welcome_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries in the AI Album flow"""
        query = update.callback_query
        
        # Log callback data for debugging
        logger.info(f"AI Album flow handle_callback received: {query.data}")
        
        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Failed to answer AI Album callback query: {e}")
            # Continue processing even if answer fails
        
        data = query.data
        
        try:
            logger.info(f"Processing AI Album callback data: {data}")
            
            if data == "ai_album":
                # Start the AI Album flow
                logger.info("Starting AI Album flow")
                await self.start_conversation(update, context)
            elif data.startswith("ai_album_track_count_"):
                track_count = int(data.split("_")[-1])
                logger.info(f"Track count selected: {track_count}")
                await self._handle_track_count_callback(query, track_count)
            elif data.startswith("ai_album_genre_"):
                genre = data.split("_", 3)[-1]
                logger.info(f"Genre selected: {genre}")
                await self._handle_genre_callback(query, genre)
            elif data.startswith("ai_album_language_"):
                language = data.split("_", 3)[-1]
                logger.info(f"Language selected: {language}")
                await self._handle_language_callback(query, language)
            elif data.startswith("ai_album_mood_"):
                mood = data.split("_", 3)[-1]
                logger.info(f"Mood selected: {mood}")
                await self._handle_mood_callback(query, mood)
            elif data.startswith("ai_album_activity_"):
                activity = data.split("_", 3)[-1]
                logger.info(f"Activity selected: {activity}")
                await self._handle_activity_callback(query, activity)
            elif data == "ai_album_custom_genre":
                logger.info("Custom genre option selected")
                await self._ask_for_custom_genre(query)
            elif data == "ai_album_custom_language":
                logger.info("Custom language option selected")
                await self._ask_for_custom_language(query)
            elif data == "ai_album_skip_genre":
                logger.info("Skip genre option selected")
                await self._handle_genre_callback(query, None)
            elif data == "ai_album_skip_language":
                logger.info("Skip language option selected")
                await self._handle_language_callback(query, None)
            elif data == "ai_album_skip_mood":
                logger.info("Skip mood option selected")
                await self._handle_mood_callback(query, None)
            else:
                logger.error(f"Unknown callback data in AI Album flow: {data}")
                await query.edit_message_text("❌ Invalid callback data")
                
        except Exception as e:
            logger.error(f"Error in AI Album callback: {e}")
            await query.edit_message_text(
                "❌ An error occurred. Please try again.",
                reply_markup=get_back_to_main_menu()
            )
            self._reset_state()
    
    async def handle_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text responses in the AI Album flow"""
        user_message = update.message.text.strip()
        
        try:
            if self.state == AIAlbumState.ASKING_GENRE:
                await self._handle_custom_genre_response(update, user_message)
            elif self.state == AIAlbumState.ASKING_LANGUAGE:
                await self._handle_custom_language_response(update, user_message)
            elif self.state == AIAlbumState.ASKING_PLAYLIST_NAME:
                await self._handle_playlist_name_response(update, user_message)
            else:
                await update.message.reply_text("❌ Invalid state. Please start over.")
                
        except Exception as e:
            logger.error(f"Error in AI Album flow: {e}")
            await update.message.reply_text(
                "❌ An error occurred. Please try again.",
                reply_markup=get_back_to_main_menu()
            )
            self._reset_state()
    
    async def _handle_track_count_callback(self, query, track_count: int):
        """Handle track count selection"""
        self.track_count = track_count
        self.state = AIAlbumState.ASKING_GENRE
        genres = self.openrouter_client.get_genres()
        # Показываем до 20 жанров
        genre_items = list(genres.items())[:20]
        keyboard = []
        for i in range(0, len(genre_items), 3):
            row = []
            for j in range(3):
                if i + j < len(genre_items):
                    key, value = genre_items[i + j]
                    row.append(InlineKeyboardButton(value, callback_data=f"ai_album_genre_{key}"))
            if row:
                keyboard.append(row)
        # Кнопка 'Пропустить' и 'Свой жанр'
        keyboard.append([
            InlineKeyboardButton("⏭️ Пропустить", callback_data="ai_album_skip_genre"),
            InlineKeyboardButton("✏️ Свой жанр", callback_data="ai_album_custom_genre")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Great! You selected {track_count} tracks.\n\nNow, what genre would you like?",
            reply_markup=reply_markup
        )
    
    async def _handle_genre_callback(self, query, genre: Optional[str]):
        """Handle genre selection"""
        if genre:
            self.genre = genre
            genre_name = self.openrouter_client.get_genres().get(genre, genre)
            message = f"Selected genre: {genre_name}\n\n"
        else:
            message = "No genre filter selected.\n\n"
        
        self.state = AIAlbumState.ASKING_LANGUAGE
        
        # Get available languages
        languages = self.openrouter_client.get_languages()
        
        # Показываем до 20 языков
        language_items = list(languages.items())[:20]
        
        keyboard = []
        for i in range(0, len(language_items), 2):
            row = []
            for j in range(2):
                if i + j < len(language_items):
                    key, value = language_items[i + j]
                    row.append(InlineKeyboardButton(value, callback_data=f"ai_album_language_{key}"))
            if row:
                keyboard.append(row)
        
        # Кнопка 'Пропустить' и 'Свой язык'
        keyboard.append([
            InlineKeyboardButton("⏭️ Пропустить", callback_data="ai_album_skip_language"),
            InlineKeyboardButton("✏️ Свой язык", callback_data="ai_album_custom_language")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message + "What language would you prefer?",
            reply_markup=reply_markup
        )
    
    async def _handle_language_callback(self, query, language: Optional[str]):
        """Handle language selection"""
        if language:
            self.language = language
            language_name = self.openrouter_client.get_languages().get(language, language)
            message = f"Selected language: {language_name}\n\n"
        else:
            message = "No language filter selected.\n\n"
        
        self.state = AIAlbumState.ASKING_MOOD
        
        # Get available moods
        moods = self.openrouter_client.get_moods()
        
        # Create keyboard with moods (3 columns)
        keyboard = []
        mood_items = list(moods.items())
        
        for i in range(0, len(mood_items), 3):
            row = []
            for j in range(3):
                if i + j < len(mood_items):
                    key, value = mood_items[i + j]
                    row.append(InlineKeyboardButton(value, callback_data=f"ai_album_mood_{key}"))
            keyboard.append(row)
        
        # Add skip button at the bottom
        keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data="ai_album_skip_mood")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message + "What mood are you looking for?",
            reply_markup=reply_markup
        )
    
    async def _handle_mood_callback(self, query, mood: Optional[str]):
        """Handle mood selection"""
        if mood:
            self.mood = mood
            mood_name = self.openrouter_client.get_moods().get(mood, mood)
            message = f"Selected mood: {mood_name}\n\n"
        else:
            message = "No mood filter selected.\n\n"
        
        self.state = AIAlbumState.ASKING_ACTIVITY
        
        # Create keyboard with activities
        activities = {
            'workout': '🏃‍♂️ Тренировка',
            'study': '📚 Учеба',
            'work': '💼 Работа',
            'relax': '😌 Отдых',
            'party': '🎉 Вечеринка',
            'travel': '✈️ Путешествие',
            'sleep': '😴 Сон',
            'general': '🎵 Общее'
        }
        
        keyboard = []
        activity_items = list(activities.items())
        
        for i in range(0, len(activity_items), 2):
            row = []
            for j in range(2):
                if i + j < len(activity_items):
                    key, value = activity_items[i + j]
                    row.append(InlineKeyboardButton(value, callback_data=f"ai_album_activity_{key}"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message + "What activity would you like to focus on?",
            reply_markup=reply_markup
        )
    
    async def _handle_activity_callback(self, query, activity: str):
        """Handle activity selection"""
        self.activity = activity
        
        activity_names = {
            'workout': 'Тренировка',
            'study': 'Учеба', 
            'work': 'Работа',
            'relax': 'Отдых',
            'party': 'Вечеринка',
            'travel': 'Путешествие',
            'sleep': 'Сон',
            'general': 'Общее'
        }
        
        activity_name = activity_names.get(activity, activity)
        
        self.state = AIAlbumState.ASKING_PLAYLIST_NAME
        
        await query.edit_message_text(
            f"Selected activity: {activity_name}\n\n"
            "What would you like to name your playlist?\n\n"
            "Please type the playlist name:"
        )
    
    async def _ask_for_custom_genre(self, query):
        """Ask user to input custom genre"""
        self.state = AIAlbumState.ASKING_GENRE
        
        await query.edit_message_text(
            "Пожалуйста, введите свой жанр текстом:\n\nПример: synthwave, vaporwave, lo-fi, ambient и т.д."
        )
    
    async def _ask_for_custom_language(self, query):
        """Ask user to input custom language"""
        self.state = AIAlbumState.ASKING_LANGUAGE
        
        await query.edit_message_text(
            "Пожалуйста, введите свой язык текстом:\n\nПример: swedish, norwegian, finnish, dutch и т.д."
        )
    
    async def _handle_custom_genre_response(self, update: Update, user_message: str):
        """Handle custom genre input"""
        self.custom_genre = user_message.strip()
        self.state = AIAlbumState.ASKING_LANGUAGE
        
        # Get available languages
        languages = self.openrouter_client.get_languages()
        
        # Create keyboard with languages (2 columns)
        keyboard = []
        language_items = list(languages.items())
        
        for i in range(0, len(language_items), 2):
            row = []
            for j in range(2):
                if i + j < len(language_items):
                    key, value = language_items[i + j]
                    row.append(InlineKeyboardButton(value, callback_data=f"ai_album_language_{key}"))
            keyboard.append(row)
        
        # Add skip and custom options
        keyboard.append([
            InlineKeyboardButton("⏭️ Пропустить", callback_data="ai_album_skip_language"),
            InlineKeyboardButton("✏️ Другой язык", callback_data="ai_album_custom_language")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Custom genre: {self.custom_genre}\n\n"
            "What language would you prefer?",
            reply_markup=reply_markup
        )
    
    async def _handle_custom_language_response(self, update: Update, user_message: str):
        """Handle custom language input"""
        self.custom_language = user_message.strip()
        self.state = AIAlbumState.ASKING_MOOD
        
        # Get available moods
        moods = self.openrouter_client.get_moods()
        
        # Create keyboard with moods (3 columns)
        keyboard = []
        mood_items = list(moods.items())
        
        for i in range(0, len(mood_items), 3):
            row = []
            for j in range(3):
                if i + j < len(mood_items):
                    key, value = mood_items[i + j]
                    row.append(InlineKeyboardButton(value, callback_data=f"ai_album_mood_{key}"))
            row.append(InlineKeyboardButton("⏭️ Пропустить", callback_data="ai_album_skip_mood"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Custom language: {self.custom_language}\n\n"
            "What mood are you looking for?",
            reply_markup=reply_markup
        )
    
    async def _handle_playlist_name_response(self, update: Update, user_message: str):
        """Handle playlist name response"""
        self.playlist_name = user_message.strip()
        
        if not self.playlist_name:
            await update.message.reply_text("❌ Please provide a playlist name.")
            return
        
        self.state = AIAlbumState.CREATING_PLAYLIST
        
        # Start creating the playlist
        await self._create_playlist(update)
    
    async def _create_playlist(self, update: Update):
        """Create the AI-generated playlist"""
        try:
            if not self.openrouter_client:
                await update.message.reply_text(
                    "❌ OpenRouter API is not configured. Please contact administrator.",
                    reply_markup=get_back_to_main_menu()
                )
                self._reset_state()
                return
            
            # Send initial message
            await update.message.reply_text(
                "🎵 Creating your AI-generated playlist...\n"
                "This may take a few moments as I consult multiple AI models."
            )
            
            # Get user's liked tracks for filtering
            liked_tracks = set()
            try:
                user_tracks = await self.spotify_client.get_user_liked_tracks()
                for track in user_tracks:
                    track_name = f"{track['name']} - {track['artists'][0]['name']}"
                    liked_tracks.add(track_name)
                logger.info(f"Found {len(liked_tracks)} liked tracks for filtering")
            except Exception as e:
                logger.warning(f"Could not fetch liked tracks: {e}")
            
            # Get recommendations from OpenRouter
            recommendations = await self.openrouter_client.get_recommendations(
                track_count=self.track_count,
                genre=self.genre or self.custom_genre or "any",
                language=self.language or self.custom_language or "any", 
                mood=self.mood or "any",
                activity=self.activity or "general",
                liked_tracks=liked_tracks
            )
            
            if not recommendations:
                await update.message.reply_text(
                    "❌ No recommendations found. Please try different parameters.",
                    reply_markup=get_back_to_main_menu()
                )
                self._reset_state()
                return
            
            # Display recommendations first
            recommendations_text = self.openrouter_client.format_recommendations_for_display(recommendations)
            
            # Split long message if needed
            if len(recommendations_text) > 4000:
                parts = [recommendations_text[i:i+4000] for i in range(0, len(recommendations_text), 4000)]
                for i, part in enumerate(parts):
                    if i == 0:
                        await update.message.reply_text(part)
                    else:
                        await update.message.reply_text(f"(continued {i+1}/{len(parts)})\n\n{part}")
            else:
                await update.message.reply_text(recommendations_text)
            
            # Filter recommendations to only include Spotify tracks
            spotify_tracks = await self._filter_spotify_tracks(recommendations)
            
            if not spotify_tracks:
                await update.message.reply_text(
                    "❌ No tracks found on Spotify. Please try different parameters.",
                    reply_markup=get_back_to_main_menu()
                )
                self._reset_state()
                return
            
            # Truncate to requested number of tracks
            final_tracks = spotify_tracks[:self.track_count]
            
            # Get Spotify URIs for playlist creation
            track_uris = [track['spotify_uri'] for track in final_tracks if track.get('spotify_uri')]
            
            if not track_uris:
                await update.message.reply_text(
                    "❌ No valid tracks found. Please try again.",
                    reply_markup=get_back_to_main_menu()
                )
                self._reset_state()
                return
            
            # Create playlist on Spotify
            playlist_id = await self.spotify_client.create_playlist(
                user_id=str(self.user_id),
                name=self.playlist_name,
                tracks=track_uris
            )
            
            if not playlist_id:
                await update.message.reply_text(
                    "❌ Failed to create playlist on Spotify. Please try again.",
                    reply_markup=get_back_to_main_menu()
                )
                self._reset_state()
                return
            
            # Get playlist URL
            playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
            
            # Create success message
            success_message = (
                f"🎉 Your AI-generated playlist is ready!\n\n"
                f"📝 Name: {self.playlist_name}\n"
                f"🎵 Tracks: {len(track_uris)}\n"
                f"🔗 Link: {playlist_url}\n\n"
                f"Parameters used:\n"
                f"• Genre: {self.custom_genre or self.genre or 'Any'}\n"
                f"• Language: {self.custom_language or self.language or 'Any'}\n"
                f"• Mood: {self.mood or 'Any'}\n"
                f"• Activity: {self.activity or 'General'}"
            )
            
            await update.message.reply_text(
                success_message,
                reply_markup=get_back_to_main_menu()
            )
            
            # Reset state
            self._reset_state()
            
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            await update.message.reply_text(
                "❌ An error occurred while creating your playlist. Please try again.",
                reply_markup=get_back_to_main_menu()
            )
            self._reset_state()
    
    async def _filter_spotify_tracks(self, recommendations) -> List[Dict]:
        """Filter recommendations to only include tracks available on Spotify"""
        try:
            filtered_recs = []
            
            for rec in recommendations:
                # Try to find the track on Spotify
                try:
                    # Search for the track on Spotify
                    search_query = f"{rec.title} {rec.artist}"
                    spotify_tracks = await self.spotify_client.search_tracks(search_query, limit=1)
                    
                    if spotify_tracks:
                        track = spotify_tracks[0]
                        # Add Spotify data to recommendation
                        filtered_rec = {
                            'title': rec.title,
                            'artist': rec.artist,
                            'genre': rec.genre,
                            'language': rec.language,
                            'reason': rec.reason,
                            'spotify_id': track['id'],
                            'spotify_uri': f"spotify:track:{track['id']}",
                            'spotify_name': track['name'],
                            'spotify_artist': track['artists'][0]['name'] if track['artists'] else rec.artist
                        }
                        filtered_recs.append(filtered_rec)
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
    
    def _reset_state(self):
        """Reset the conversation state"""
        self.state = AIAlbumState.IDLE
        self.track_count = None
        self.genre = None
        self.custom_genre = None
        self.language = None
        self.custom_language = None
        self.mood = None
        self.activity = None
        self.playlist_name = None 