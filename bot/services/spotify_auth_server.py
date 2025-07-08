"""
Spotify OAuth web server for handling authorization callbacks
Now designed to run within the main bot's asyncio event loop.
"""

import logging
from aiohttp import web
from bot.utils.config import get_redirect_uri
from bot.services.user_settings import UserSettings
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

logger = logging.getLogger(__name__)

class SpotifyAuthServer:
    """Web server for handling Spotify OAuth callback only. Runs in-process."""
    def __init__(self):
        self.app = web.Application()
        self.app.router.add_get('/callback', self.handle_callback)
        self.user_settings = UserSettings()
        self.runner = None
        self.site = None

    async def start(self, host='0.0.0.0', port=8888):
        """Starts the server non-blockingly as part of an existing asyncio loop."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, host, port)
            await self.site.start()
            logger.info(f"✅ Auth server started successfully on http://{host}:{port}")
        except Exception as e:
            logger.error(f"Failed to start auth server: {e}", exc_info=True)
            # Propagate the exception to stop the bot from starting with a broken component.
            raise

    async def stop(self):
        """Stops the server gracefully."""
        if self.site:
            await self.site.stop()
            logger.info("Auth server site stopped.")
        if self.runner:
            await self.runner.cleanup()
            logger.info("Auth server runner cleaned up.")

    async def handle_callback(self, request):
        # The robust callback handler from before
        state = request.query.get('state', 'unknown_user')
        try:
            code = request.query.get('code')
            error = request.query.get('error')

            if error:
                logger.error(f"Spotify auth error from callback for user {state}: {error}")
                return web.Response(
                    text=f"<html><body><h1>Ошибка авторизации от Spotify</h1><p>{error}</p><p>Пожалуйста, вернитесь в бот и попробуйте снова.</p></body></html>",
                    content_type='text/html'
                )
            
            if not code or not state:
                logger.error("Callback received without code or state.")
                return web.Response(
                    text="<html><body><h1>Ошибка</h1><p>Отсутствует код авторизации или state. Попробуйте пройти авторизацию заново.</p></body></html>",
                    content_type='text/html'
                )

            try:
                user_id = int(state)
            except (ValueError, TypeError):
                logger.error(f"Invalid state received in callback: {state}")
                return web.Response(
                    text="<html><body><h1>Ошибка</h1><p>Неверный state. Попробуйте пройти авторизацию заново.</p></body></html>",
                    content_type='text/html'
                )

            credentials = self.user_settings.get_spotify_credentials(user_id)
            if not credentials:
                logger.error(f"No credentials found for user_id from state: {user_id}")
                return web.Response(
                    text="<html><body><h1>Ошибка</h1><p>Ваши настройки не найдены. Пожалуйста, начните сначала, отправив /start в боте.</p></body></html>",
                    content_type='text/html'
                )

            redirect_uri = get_redirect_uri()
            if not redirect_uri:
                logger.error("Redirect URI is not configured in the bot.")
                return web.Response(
                    text="<html><body><h1>Критическая ошибка конфигурации</h1><p>Redirect URI не настроен в боте. Обратитесь к администратору.</p></body></html>",
                    content_type='text/html'
                )
            
            scope = (
                "user-top-read user-read-recently-played playlist-modify-public "
                "playlist-modify-private user-library-read"
            )

            sp_oauth = SpotifyOAuth(
                client_id=credentials["client_id"],
                client_secret=credentials["client_secret"],
                redirect_uri=redirect_uri,
                scope=scope,
                state=str(user_id),
                open_browser=False
            )
            
            token_info = sp_oauth.get_access_token(code, check_cache=False)
            
            self.user_settings.save_spotify_tokens(
                user_id,
                token_info['access_token'],
                token_info['refresh_token'],
                token_info['expires_in']
            )

            success_html = """
            <html><head><title>Авторизация успешна</title><style>body{font-family:-apple-system,system-ui,sans-serif;background-color:#f0f2f5;text-align:center;padding-top:50px}div{background-color:white;padding:40px;border-radius:10px;display:inline-block;box-shadow:0 4px 8px rgba(0,0,0,0.1)}h1{color:#1DB954}p{color:#555}</style></head>
            <body><div><h1>✅ Успешно!</h1><p>Авторизация в Spotify прошла успешно. Можете вернуться в Telegram.</p></div></body></html>
            """
            return web.Response(text=success_html, content_type='text/html')

        except SpotifyOauthError as e:
            logger.error(f"Spotify OAuth Error during token exchange for user {state}: {e}", exc_info=True)
            debug_message = (
                "<h1>Ошибка авторизации Spotify</h1>"
                "<p>Spotify сообщает об ошибке. Чаще всего это несоответствие Redirect URI.</p>"
                f"<p><b>Детали ошибки:</b> <pre>{e}</pre></p>"
                "<p>Убедитесь, что Redirect URI в <a href='https://developer.spotify.com/dashboard'>Spotify Developer Dashboard</a> <b>ТОЧЬ-В-ТОЧЬ</b> совпадает с тем, который использует бот.</p>"
            )
            return web.Response(text=f"<html><body>{debug_message}</body></html>", content_type='text/html', status=400)

        except Exception as e:
            logger.error(f"FATAL: Unhandled exception in auth callback for user {state}: {e}", exc_info=True)
            return web.Response(
                text="<html><body><h1>Критическая ошибка сервера</h1><p>Произошла непредвиденная ошибка при обработке вашего запроса. Пожалуйста, сообщите администратору.</p></body></html>",
                content_type='text/html',
                status=500
            )

# Global instance to be used by the main application
auth_server = SpotifyAuthServer() 