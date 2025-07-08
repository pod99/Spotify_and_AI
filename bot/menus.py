"""
Telegram bot menu builders
"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    """Get main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎵 My Music", callback_data="my_music")],
        [InlineKeyboardButton("📊 Analytics", callback_data="analytics")],
        [InlineKeyboardButton("🤖 AI Album", callback_data="ai_album")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_analytics_menu():
    """Get analytics submenu keyboard"""
    keyboard = [
        [InlineKeyboardButton("📈 Top Tracks", callback_data="analytics_top_tracks")],
        [InlineKeyboardButton("🎵 Top Artists", callback_data="analytics_top_artists")],
        [InlineKeyboardButton("🕐 Listening Activity", callback_data="analytics_activity")],
        [InlineKeyboardButton("🎼 Top Genres", callback_data="analytics_genres")],
        [InlineKeyboardButton("📅 Release Years", callback_data="analytics_years")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ai_album_track_count_menu():
    """Get AI Album track count selection menu"""
    keyboard = [
        [
            InlineKeyboardButton("15", callback_data="ai_album_track_count_15"),
            InlineKeyboardButton("25", callback_data="ai_album_track_count_25"),
            InlineKeyboardButton("40", callback_data="ai_album_track_count_40")
        ],
        [
            InlineKeyboardButton("60", callback_data="ai_album_track_count_60"),
            InlineKeyboardButton("100", callback_data="ai_album_track_count_100"),
            InlineKeyboardButton("150", callback_data="ai_album_track_count_150")
        ],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ai_album_genre_menu():
    """Get AI Album genre selection menu"""
    keyboard = [
        [
            InlineKeyboardButton("🎵 Pop", callback_data="ai_album_genre_pop"),
            InlineKeyboardButton("🎸 Rock", callback_data="ai_album_genre_rock"),
            InlineKeyboardButton("🎧 Electronic", callback_data="ai_album_genre_electronic")
        ],
        [
            InlineKeyboardButton("🎤 Hip Hop", callback_data="ai_album_genre_hip-hop"),
            InlineKeyboardButton("🎷 Jazz", callback_data="ai_album_genre_jazz"),
            InlineKeyboardButton("🎼 Classical", callback_data="ai_album_genre_classical")
        ],
        [
            InlineKeyboardButton("🎹 Indie", callback_data="ai_album_genre_indie"),
            InlineKeyboardButton("🌊 Alternative", callback_data="ai_album_genre_alternative"),
            InlineKeyboardButton("💃 Dance", callback_data="ai_album_genre_dance")
        ],
        [
            InlineKeyboardButton("⏭️ Skip Genre", callback_data="ai_album_skip_genre"),
            InlineKeyboardButton("🔙 Back", callback_data="ai_album_back")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ai_album_mood_menu():
    """Get AI Album mood selection menu"""
    keyboard = [
        [
            InlineKeyboardButton("😊 Happy", callback_data="ai_album_mood_happy"),
            InlineKeyboardButton("😌 Calm", callback_data="ai_album_mood_calm")
        ],
        [
            InlineKeyboardButton("😢 Sad", callback_data="ai_album_mood_sad"),
            InlineKeyboardButton("💃 Danceable", callback_data="ai_album_mood_danceable")
        ],
        [
            InlineKeyboardButton("⏭️ Skip Mood", callback_data="ai_album_skip_mood"),
            InlineKeyboardButton("🔙 Back", callback_data="ai_album_back")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_main_menu():
    """Get back to main menu button"""
    keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_menu():
    """Get cancel button"""
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard) 