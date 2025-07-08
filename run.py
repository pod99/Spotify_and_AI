#!/usr/bin/env python3
"""
Main entry point for the Spotify & Yambda Telegram Bot
"""

import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.handlers import (
    start_command,
    handle_main_menu_callback,
    handle_analytics_callback,
    handle_ai_album_flow_callback,
    handle_text_message
)
from bot.utils.config import load_config
from bot.services.spotify_auth_server import auth_server # Import the server instance

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to start the bot and the integrated auth server."""
    config = load_config()

    application = Application.builder().token(config['BOT_TOKEN']).build()

    # Register handlers from other modules
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_main_menu_callback, pattern="^(my_music|analytics|ai_album|back_to_main)$"))
    application.add_handler(CallbackQueryHandler(handle_analytics_callback, pattern="^analytics_"))
    application.add_handler(CallbackQueryHandler(handle_ai_album_flow_callback, pattern="^ai_album_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    async def error_handler(update, context):
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
        if update and hasattr(update, 'message') and update.message:
            try:
                await update.message.reply_text("❌ Произошла внутренняя ошибка. Попробуйте снова позже.")
            except Exception as e:
                logger.error(f"Failed to send error message to user: {e}")

    application.add_error_handler(error_handler)

    # The `async with` statement gracefully handles application startup and shutdown.
    # This includes calling initialize() and shutdown().
    logger.info("Starting bot and auth server...")
    async with application:
        try:
            # Start our custom auth server first
            await auth_server.start()
            
            # Start the Telegram bot components
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            
            logger.info("✅ Bot is running! Press Ctrl-C to stop.")
            
            # Keep the application running indefinitely until a stop signal is received
            await asyncio.Event().wait()

        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutdown signal received.")
        finally:
            # The `async with` block ensures `application.shutdown()` is called.
            # We add our custom server's stop logic here to ensure it also cleans up.
            logger.info("Stopping auth server...")
            await auth_server.stop()
            logger.info("Bot shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This is to catch the final Ctrl-C and exit cleanly without a traceback
        logger.info("Program finished.") 