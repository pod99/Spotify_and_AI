"""
Configuration utility for loading environment variables
"""

import os
import logging
from typing import Dict
from dotenv import load_dotenv
import requests

logger = logging.getLogger(__name__)

def get_current_ngrok_domain() -> str:
    """Try to get the current ngrok domain from the local ngrok API."""
    try:
        resp = requests.get("http://localhost:4040/api/tunnels", timeout=1)
        data = resp.json()
        for tunnel in data.get("tunnels", []):
            public_url = tunnel.get("public_url", "")
            if public_url.startswith("https://") and ".ngrok-free.app" in public_url:
                return public_url.replace("https://", "")
    except Exception as e:
        logger.debug(f"Could not fetch ngrok domain from API: {e}")
    return None

def load_config() -> Dict[str, str]:
    """Load configuration from environment variables"""
    # Load .env file if it exists
    load_dotenv()
    
    config = {
        'BOT_TOKEN': os.getenv('BOT_TOKEN'),
        'SPOTIFY_CLIENT_ID': os.getenv('SPOTIFY_CLIENT_ID'),
        'SPOTIFY_CLIENT_SECRET': os.getenv('SPOTIFY_CLIENT_SECRET'),
        'YAMBDA_API_KEY': os.getenv('YAMBDA_API_KEY'),
        'OPENROUTER_API_KEY': os.getenv('OPENROUTER_API_KEY'),
    }
    
    # Always get the latest ngrok domain if possible
    ngrok_domain = get_current_ngrok_domain() or os.getenv('NGROK_DOMAIN')
    config['NGROK_DOMAIN'] = ngrok_domain
    
    # Validate required configuration
    missing_vars = []
    for key, value in config.items():
        if key in ['BOT_TOKEN'] and not value:  # Only BOT_TOKEN is required initially
            missing_vars.append(key)
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    return config

def get_config_value(key: str, default: str = None) -> str:
    """Get a specific configuration value"""
    config = load_config()
    return config.get(key, default)

def get_redirect_uri() -> str:
    """Get Spotify redirect URI using ngrok domain"""
    ngrok_domain = get_config_value('NGROK_DOMAIN')
    if ngrok_domain:
        return f"https://{ngrok_domain}/callback"
    else:
        return "http://localhost:8888/callback" 