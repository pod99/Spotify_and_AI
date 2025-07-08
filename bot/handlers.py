"""
Telegram bot handlers for commands and callbacks
"""

import logging
from telegram import Update, InputMediaPhoto, InputMediaDocument, InputMediaVideo, InputMediaAudio, InputMediaAnimation, InputMedia
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.constants import ParseMode

from bot.menus import (
    get_main_menu,
    get_analytics_menu,
    get_ai_album_track_count_menu,
    get_ai_album_genre_menu,
    get_ai_album_mood_menu,
    get_back_to_main_menu,
    get_cancel_menu
)
from bot.services.spotify_client import SpotifyClient
from bot.services.history_manager import HistoryManager
from bot.services.analytics import AnalyticsService
from bot.services.ai_album_flow import AIAlbumFlow, AIAlbumState
from bot.services.setup_flow import SetupFlow
from bot.services.user_settings import UserSettings

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    # Check if user needs setup
    user_settings = UserSettings()
    if not user_settings.is_user_setup_complete(user_id):
        # Start setup flow
        setup_flow = SetupFlow(user_id)
        context.user_data['setup_flow'] = setup_flow
        await setup_flow.start_setup(update, context)
        return
    
    # User is already set up, show main menu
    await update.message.reply_text(
        "🎵 Welcome to Spotify & Yambda Bot!\n\nChoose an option:",
        reply_markup=get_main_menu()
    )

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu selection (called from callback)"""
    user_id = update.effective_user.id
    
    # Check if user needs setup
    user_settings = UserSettings()
    if not user_settings.is_user_setup_complete(user_id):
        await update.message.reply_text(
            "❌ Пожалуйста, сначала завершите настройку Spotify.\n"
            "Отправьте /start для начала настройки."
        )
        return
    
    try:
        spotify_client = SpotifyClient(user_id)
        
        # Check if user is authorized with Spotify
        if not spotify_client.is_authorized():
            auth_url = spotify_client.get_auth_url()
            if auth_url:
                await update.message.reply_text(
                    "🔐 **Требуется авторизация Spotify**\n\n"
                    "Для доступа к вашей музыке необходимо авторизоваться в Spotify.\n\n"
                    f"🔗 [Нажмите здесь для авторизации]({auth_url})\n\n"
                    "После авторизации попробуйте снова.",
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка получения ссылки авторизации. Проверьте настройки NGROK_DOMAIN."
                )
            return
        
        # Получаем последние 20 треков из истории прослушиваний
        recent_tracks = await spotify_client.get_recently_played(user_id, limit=20)
        
        if not recent_tracks:
            await update.message.reply_text(
                "❌ Нет данных о недавних прослушиваниях.\n"
                "Попробуйте послушать музыку через Spotify и вернитесь позже."
            )
            return
        
        response = "🎵 Ваши последние 20 прослушанных треков:\n\n"
        for i, track in enumerate(recent_tracks, 1):
            artists = ", ".join([artist['name'] for artist in track['artists']])
            played_at = track.get('played_at', 'Неизвестно')
            if played_at != 'Неизвестно':
                # Форматируем время прослушивания
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(played_at.replace('Z', '+00:00'))
                    played_at = dt.strftime("%d.%m %H:%M")
                except:
                    played_at = "Недавно"
            
            response += f"{i}. {track['name']} — {artists}\n   🕐 {played_at}\n"
        
        response += "\n🔄 Данные обновляются каждые 15 минут"
        
        await update.message.reply_text(response, reply_markup=get_back_to_main_menu())
        
    except Exception as e:
        logger.error(f"Error in main menu handler: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении данных о вашей музыке.")

async def handle_analytics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle analytics menu selection"""
    user_id = update.effective_user.id
    
    # Check if user needs setup
    user_settings = UserSettings()
    if not user_settings.is_user_setup_complete(user_id):
        await update.message.reply_text(
            "❌ Пожалуйста, сначала завершите настройку Spotify.\n"
            "Отправьте /start для начала настройки."
        )
        return
    
    # Check if user is authorized with Spotify
    spotify_client = SpotifyClient(user_id)
    if not spotify_client.is_authorized():
        auth_url = spotify_client.get_auth_url()
        if auth_url:
            await update.message.reply_text(
                "🔐 **Требуется авторизация Spotify**\n\n"
                "Для доступа к аналитике необходимо авторизоваться в Spotify.\n\n"
                f"🔗 [Нажмите здесь для авторизации]({auth_url})\n\n"
                "После авторизации попробуйте снова.",
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка получения ссылки авторизации. Проверьте настройки NGROK_DOMAIN."
            )
        return
    
    await update.message.reply_text(
        "📊 Choose an analytics type:",
        reply_markup=get_analytics_menu()
    )

async def handle_analytics_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle analytics menu selection from callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Check if user needs setup
    user_settings = UserSettings()
    if not user_settings.is_user_setup_complete(user_id):
        await query.message.edit_text(
            "❌ Пожалуйста, сначала завершите настройку Spotify.\n"
            "Отправьте /start для начала настройки.",
            reply_markup=get_back_to_main_menu()
        )
        return
    
    # Check if user is authorized with Spotify
    spotify_client = SpotifyClient(user_id)
    if not spotify_client.is_authorized():
        auth_url = spotify_client.get_auth_url()
        if auth_url:
            await query.message.edit_text(
                "🔐 **Требуется авторизация Spotify**\n\n"
                "Для доступа к аналитике необходимо авторизоваться в Spotify.\n\n"
                f"🔗 [Нажмите здесь для авторизации]({auth_url})\n\n"
                "После авторизации попробуйте снова.",
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=get_back_to_main_menu()
            )
        else:
            await query.message.edit_text(
                "❌ Ошибка получения ссылки авторизации. Проверьте настройки NGROK_DOMAIN.",
                reply_markup=get_back_to_main_menu()
            )
        return
    
    await query.message.edit_text(
        "📊 Choose an analytics type:",
        reply_markup=get_analytics_menu()
    )

async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu button clicks"""
    query = update.callback_query
    
    # Log callback data for debugging
    logger.info(f"Main menu callback received: {query.data}")
    
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Failed to answer callback query: {e}")
        # Continue processing even if answer fails
    
    if query.data == "my_music":
        # Call handle_main_menu with a compatible object
        # Instead of creating a fake Update, call the handler logic directly
        # We'll refactor handle_main_menu to accept message and user_id
        await handle_main_menu_from_callback(query.message, context, update.effective_user.id)
    elif query.data == "analytics":
        await handle_analytics_menu_callback(update, context)
    elif query.data == "ai_album":
        logger.info("AI Album button clicked, starting flow...")
        await handle_ai_album_flow_callback(update, context)
    elif query.data == "back_to_main":
        # Попытка заменить media на текст, если это не текстовое сообщение
        try:
            await query.message.edit_text(
                "🎵 Welcome to Spotify & Yambda Bot!\n\nChoose an option:",
                reply_markup=get_main_menu()
            )
        except Exception as e:
            if "no text in the message to edit" in str(e).lower() or "message is not modified" in str(e).lower() or "file must be non-empty" in str(e).lower():
                # Если сообщение не текстовое (например, это график), удаляем его и отправляем новое
                await query.message.delete()
                await query.message.chat.send_message(
                    "🎵 Welcome to Spotify & Yambda Bot!\n\nChoose an option:",
                    reply_markup=get_main_menu()
                )
            else:
                raise
    else:
        logger.error(f"Unknown callback data in main menu: {query.data}")
        await query.message.edit_text(
            "❌ Unknown option. Please try again.",
            reply_markup=get_main_menu()
        )

# New helper for callback context
async def handle_main_menu_from_callback(message, context, user_id):
    user_settings = UserSettings()
    if not user_settings.is_user_setup_complete(user_id):
        await message.reply_text(
            "❌ Пожалуйста, сначала завершите настройку Spotify.\n"
            "Отправьте /start для начала настройки."
        )
        return
    try:
        spotify_client = SpotifyClient(user_id)
        if not spotify_client.is_authorized():
            auth_url = spotify_client.get_auth_url()
            if auth_url:
                await message.reply_text(
                    "🔐 **Требуется авторизация Spotify**\n\n"
                    "Для доступа к вашей музыке необходимо авторизоваться в Spotify.\n\n"
                    f"🔗 [Нажмите здесь для авторизации]({auth_url})\n\n"
                    "После авторизации попробуйте снова.",
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            else:
                await message.reply_text(
                    "❌ Ошибка получения ссылки авторизации. Проверьте настройки NGROK_DOMAIN."
                )
            return
        recent_tracks = await spotify_client.get_recently_played(user_id, limit=20)
        if not recent_tracks:
            await message.reply_text(
                "❌ Нет данных о недавних прослушиваниях.\n"
                "Попробуйте послушать музыку через Spotify и вернитесь позже."
            )
            return
        response = "🎵 Ваши последние 20 прослушанных треков:\n\n"
        for i, track in enumerate(recent_tracks, 1):
            artists = ", ".join([artist['name'] for artist in track['artists']])
            played_at = track.get('played_at', 'Неизвестно')
            if played_at != 'Неизвестно':
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(played_at.replace('Z', '+00:00'))
                    played_at = dt.strftime("%d.%m %H:%M")
                except:
                    played_at = "Недавно"
            response += f"{i}. {track['name']} — {artists}\n   🕐 {played_at}\n"
        response += "\n🔄 Данные обновляются каждые 15 минут"
        await message.reply_text(response, reply_markup=get_back_to_main_menu())
    except Exception as e:
        logger.error(f"Error in main menu handler (callback): {e}")
        await message.reply_text("❌ Произошла ошибка при получении данных о вашей музыке.")

async def handle_ai_album_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle AI Album flow callbacks"""
    query = update.callback_query
    
    # Log callback data for debugging
    logger.info(f"AI Album flow callback received: {query.data}")
    
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Failed to answer AI Album callback query: {e}")
        # Continue processing even if answer fails
    
    user_id = update.effective_user.id
    logger.info(f"Processing AI Album callback for user {user_id}")
    
    # Check if user needs setup
    user_settings = UserSettings()
    if not user_settings.is_user_setup_complete(user_id):
        logger.warning(f"User {user_id} not set up, redirecting to setup")
        await query.message.edit_text(
            "❌ Пожалуйста, сначала завершите настройку Spotify.\n"
            "Отправьте /start для начала настройки.",
            reply_markup=get_back_to_main_menu()
        )
        return
    
    # Check if user is authorized with Spotify
    spotify_client = SpotifyClient(user_id)
    if not spotify_client.is_authorized():
        logger.warning(f"User {user_id} not authorized with Spotify")
        auth_url = spotify_client.get_auth_url()
        if auth_url:
            await query.message.edit_text(
                "🔐 **Требуется авторизация Spotify**\n\n"
                "Для создания плейлистов необходимо авторизоваться в Spotify.\n\n"
                f"🔗 [Нажмите здесь для авторизации]({auth_url})\n\n"
                "После авторизации попробуйте снова.",
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=get_back_to_main_menu()
            )
        else:
            await query.message.edit_text(
                "❌ Ошибка получения ссылки авторизации. Проверьте настройки NGROK_DOMAIN.",
                reply_markup=get_back_to_main_menu()
            )
        return
    
    # Initialize AI Album flow if not exists
    if 'ai_album_flow' not in context.user_data:
        logger.info(f"Creating new AI Album flow for user {user_id}")
        ai_flow = AIAlbumFlow(user_id)
        context.user_data['ai_album_flow'] = ai_flow
    
    ai_flow = context.user_data['ai_album_flow']
    logger.info(f"Processing AI Album callback with flow state: {ai_flow.state}")
    
    # Handle the callback
    try:
        await ai_flow.handle_callback(update, context)
    except Exception as e:
        logger.error(f"Error in AI Album flow callback: {e}")
        await query.message.edit_text(
            "❌ Произошла ошибка. Попробуйте снова.",
            reply_markup=get_back_to_main_menu()
        )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unified text message handler that routes to appropriate handlers"""
    user_id = update.effective_user.id
    
    # Check for AI Album session first
    if 'ai_album_flow' in context.user_data:
        ai_flow = context.user_data['ai_album_flow']
        if (ai_flow.state == AIAlbumState.ASKING_GENRE or 
            ai_flow.state == AIAlbumState.ASKING_LANGUAGE or
            ai_flow.state == AIAlbumState.ASKING_PLAYLIST_NAME):
            return await handle_ai_album_response(update, context)
    
    # Check for setup session
    if 'setup_flow' in context.user_data:
        return await handle_setup_response(update, context)
    
    # If no active sessions, ignore the message
    return False

async def handle_ai_album_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle AI Album conversation responses (for custom inputs and playlist name)"""
    user_id = update.effective_user.id
    
    # Only handle if there's an active AI Album session
    if 'ai_album_flow' not in context.user_data:
        # If no AI Album session, let other handlers process this
        return False
    
    ai_flow = context.user_data['ai_album_flow']
    
    # Handle different states
    if ai_flow.state == AIAlbumState.ASKING_GENRE:
        # User is entering custom genre
        await ai_flow.handle_response(update, context)
        return True
    elif ai_flow.state == AIAlbumState.ASKING_LANGUAGE:
        # User is entering custom language
        await ai_flow.handle_response(update, context)
        return True
    elif ai_flow.state == AIAlbumState.ASKING_PLAYLIST_NAME:
        # User is entering playlist name
        await ai_flow.handle_response(update, context)
        return True
    else:
        await update.message.reply_text("❌ Invalid state. Please use the buttons.")
        return True

async def handle_setup_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setup flow responses"""
    user_id = update.effective_user.id
    
    if 'setup_flow' not in context.user_data:
        await update.message.reply_text("❌ No active setup session. Please send /start.")
        return
    
    setup_flow = context.user_data['setup_flow']
    await setup_flow.handle_response(update, context)
    
    # If setup is complete, remove from context
    if setup_flow.state.value == "idle":
        del context.user_data['setup_flow']

async def handle_analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle analytics submenu callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Check if user needs setup
    user_settings = UserSettings()
    if not user_settings.is_user_setup_complete(user_id):
        await query.message.edit_text(
            "❌ Пожалуйста, сначала завершите настройку Spotify.\n"
            "Отправьте /start для начала настройки.",
            reply_markup=get_back_to_main_menu()
        )
        return
    
    # Check if user is authorized with Spotify
    spotify_client = SpotifyClient(user_id)
    if not spotify_client.is_authorized():
        auth_url = spotify_client.get_auth_url()
        if auth_url:
            await query.message.edit_text(
                "🔐 **Требуется авторизация Spotify**\n\n"
                "Для доступа к аналитике необходимо авторизоваться в Spotify.\n\n"
                f"🔗 [Нажмите здесь для авторизации]({auth_url})\n\n"
                "После авторизации попробуйте снова.",
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=get_back_to_main_menu()
            )
        else:
            await query.message.edit_text(
                "❌ Ошибка получения ссылки авторизации. Проверьте настройки NGROK_DOMAIN.",
                reply_markup=get_back_to_main_menu()
            )
        return
    
    analytics_type = query.data
    
    try:
        analytics_service = AnalyticsService()
        
        # Get user data
        user_data = await spotify_client.get_user_data(user_id)
        
        # Generate chart
        chart_path = await analytics_service.generate_chart(
            analytics_type, user_data, user_id
        )
        
        # Send chart
        with open(chart_path, 'rb') as chart_file:
            await query.message.edit_media(
                media=InputMediaPhoto(chart_file, caption=f"📊 {analytics_type.replace('analytics_', '').replace('_', ' ').title()} Analytics")
            )
            # Вернуть кнопки аналитики после показа графика
            await query.message.edit_reply_markup(reply_markup=get_analytics_menu())
        
        # Clean up
        import os
        os.remove(chart_path)
        
        # Show menu again - only if the message content would actually change
        current_text = query.message.text or ""
        new_text = "📊 Choose another analytics type:"
        
        if current_text != new_text:
            try:
                await query.message.edit_text(
                    new_text,
                    reply_markup=get_analytics_menu()
                )
            except Exception as edit_error:
                if "Message is not modified" not in str(edit_error):
                    logger.error(f"Error editing analytics message: {edit_error}")
        else:
            # If content is the same, just answer the callback
            await query.answer("Chart generated successfully!")
        
    except Exception as e:
        logger.error(f"Error in analytics callback: {e}")
        try:
            await query.message.edit_text(
                "❌ An error occurred while generating the chart.",
                reply_markup=get_analytics_menu()
            )
        except Exception as edit_error:
            if "Message is not modified" not in str(edit_error):
                logger.error(f"Error editing error message: {edit_error}")
            await query.answer("Error generating chart") 