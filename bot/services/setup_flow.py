"""
Setup flow for user's initial configuration
"""

import logging
from typing import Dict, Optional
from enum import Enum
from telegram import Update
from telegram.ext import ContextTypes

from bot.services.user_settings import UserSettings
from bot.menus import get_main_menu

logger = logging.getLogger(__name__)

class SetupState(Enum):
    """Setup conversation states"""
    IDLE = "idle"
    ASKING_SPOTIFY_CLIENT_ID = "asking_spotify_client_id"
    ASKING_SPOTIFY_CLIENT_SECRET = "asking_spotify_client_secret"
    CONFIRMING_SETUP = "confirming_setup"

class SetupFlow:
    """Manages user setup conversation flow"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.state = SetupState.IDLE
        self.spotify_client_id = None
        self.spotify_client_secret = None
        self.user_settings = UserSettings()
    
    async def start_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the setup conversation"""
        self.state = SetupState.ASKING_SPOTIFY_CLIENT_ID
        
        setup_message = (
            "🔧 **Добро пожаловать в настройку Spotify!**\n\n"
            "Для работы с вашей музыкой мне нужны ваши Spotify API ключи.\n\n"
            "📋 **Как получить ключи:**\n"
            "1. Перейдите на [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)\n"
            "2. Создайте новое приложение\n"
            "3. Добавьте в Redirect URIs: `https://ваш-ngrok-домен.ngrok.io/callback`\n"
            "4. Скопируйте Client ID и Client Secret\n\n"
            "Введите ваш **Spotify Client ID**:"
        )
        
        await update.message.reply_text(setup_message, parse_mode='Markdown')
    
    async def handle_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user responses in the setup flow"""
        user_message = update.message.text.strip()
        
        try:
            if self.state == SetupState.ASKING_SPOTIFY_CLIENT_ID:
                await self._handle_client_id_response(update, user_message)
            elif self.state == SetupState.ASKING_SPOTIFY_CLIENT_SECRET:
                await self._handle_client_secret_response(update, user_message)
            elif self.state == SetupState.CONFIRMING_SETUP:
                await self._handle_confirmation_response(update, user_message)
            else:
                await update.message.reply_text("❌ Неверное состояние. Начните заново.")
                
        except Exception as e:
            logger.error(f"Error in setup flow: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте еще раз.",
                reply_markup=get_main_menu()
            )
            self._reset_state()
    
    async def _handle_client_id_response(self, update: Update, user_message: str):
        """Handle Spotify Client ID response"""
        if len(user_message) < 10:  # Basic validation
            await update.message.reply_text(
                "❌ Client ID слишком короткий. Пожалуйста, проверьте и введите правильный Client ID."
            )
            return
        
        self.spotify_client_id = user_message
        self.state = SetupState.ASKING_SPOTIFY_CLIENT_SECRET
        
        await update.message.reply_text(
            "✅ Client ID сохранен!\n\n"
            "Теперь введите ваш **Spotify Client Secret**:"
        )
    
    async def _handle_client_secret_response(self, update: Update, user_message: str):
        """Handle Spotify Client Secret response"""
        if len(user_message) < 10:  # Basic validation
            await update.message.reply_text(
                "❌ Client Secret слишком короткий. Пожалуйста, проверьте и введите правильный Client Secret."
            )
            return
        
        self.spotify_client_secret = user_message
        self.state = SetupState.CONFIRMING_SETUP
        
        confirmation_message = (
            "✅ Client Secret сохранен!\n\n"
            "📋 **Проверьте ваши данные:**\n"
            f"• Client ID: `{self.spotify_client_id[:10]}...`\n"
            f"• Client Secret: `{self.spotify_client_secret[:10]}...`\n\n"
            "Всё правильно? Отправьте 'да' для подтверждения или 'нет' для повторного ввода."
        )
        
        await update.message.reply_text(confirmation_message, parse_mode='Markdown')
    
    async def _handle_confirmation_response(self, update: Update, user_message: str):
        """Handle confirmation response"""
        if user_message.lower() in ['да', 'yes', 'y', '1', 'true']:
            # Save credentials
            success = self.user_settings.save_spotify_credentials(
                self.user_id,
                self.spotify_client_id,
                self.spotify_client_secret
            )
            
            if success:
                await update.message.reply_text(
                    "🎉 **Настройка завершена!**\n\n"
                    "Ваши Spotify credentials успешно сохранены.\n"
                    "Теперь вы можете использовать все функции бота!\n\n"
                    "Выберите действие:",
                    reply_markup=get_main_menu()
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при сохранении данных. Попробуйте еще раз.",
                    reply_markup=get_main_menu()
                )
            
            self._reset_state()
            
        elif user_message.lower() in ['нет', 'no', 'n', '0', 'false']:
            # Reset and start over
            self._reset_state()
            await self.start_setup(update, None)
            
        else:
            await update.message.reply_text(
                "❌ Пожалуйста, ответьте 'да' или 'нет'."
            )
    
    def _reset_state(self):
        """Reset the conversation state"""
        self.state = SetupState.IDLE
        self.spotify_client_id = None
        self.spotify_client_secret = None 