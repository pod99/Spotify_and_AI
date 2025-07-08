# Spotify & Yambda Telegram Bot

A full-featured Telegram bot that integrates with Spotify and the Yambda recommendation neural network to provide personalized music analytics and AI-generated playlists.

## Features

### 🎵 My Music
- View your top 15 most-played tracks and play counts
- Pulls data from Spotify via spotipy integration

### 📊 Analytics
Generate beautiful charts for:
- Popular Tracks
- Popular Artists  
- Activity by Hour
- Activity by Day
- Release Years Distribution
- Top Genre

### 🤖 AI Album
Create personalized playlists using AI recommendations:
1. Choose number of tracks (15, 25, 40, 60, 100, 150)
2. Select genre (or skip)
3. Choose mood (happy, calm, sad, danceable or skip)
4. Name your playlist
5. Get AI-generated playlist with Yambda recommendations

## Architecture

```
spotify_and_yandex/
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
├── run.py               # Main entry point
├── bot/
│   ├── __init__.py
│   ├── handlers.py      # Telegram bot handlers
│   ├── menus.py         # Menu builders
│   ├── services/
│   │   ├── spotify_client.py    # Spotify API wrapper
│   │   ├── yambda_client.py     # Yambda dataset integration
│   │   ├── history_manager.py   # Play history & analytics
│   │   ├── analytics.py         # Chart generation
│   │   └── ai_album_flow.py     # AI playlist creation
│   └── utils/
│       └── config.py    # Configuration loader
└── temp/                # Temporary chart storage
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and fill in your API credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `BOT_TOKEN`: Your Telegram bot token from @BotFather
- `SPOTIFY_CLIENT_ID`: Spotify API client ID
- `SPOTIFY_CLIENT_SECRET`: Spotify API client secret
- `YAMBDA_API_KEY`: Yambda API key (optional for basic functionality)

### 3. Spotify Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Add `http://localhost:8888/callback` to Redirect URIs
4. Copy Client ID and Client Secret to your `.env` file

### 4. Telegram Bot Setup

1. Message @BotFather on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token to your `.env` file

### 5. Run the Bot

```bash
python run.py
```

## Usage

1. Start the bot with `/start`
2. Choose from three main options:
   - **🎵 My Music**: View your top tracks
   - **📊 Analytics**: Generate charts
   - **🤖 AI Album**: Create AI playlists

## Dependencies

- `python-telegram-bot==20.0b1`: Telegram bot framework
- `spotipy==2.23.0`: Spotify API wrapper
- `datasets==2.17.0`: HuggingFace datasets for Yambda
- `matplotlib==3.7.2`: Chart generation
- `plotly==5.18.0`: Interactive charts
- `python-dotenv==1.0.0`: Environment variable management

## Technical Details

### Spotify Integration
- Uses spotipy for authentication and API calls
- Fetches user's top tracks and recently played
- Creates playlists with AI recommendations

### Yambda Integration
- Loads "flat/50m" dataset from HuggingFace
- Filters recommendations by genre and mood
- Cross-references with Spotify for availability

### Analytics
- Generates charts using plotly and matplotlib
- Saves charts to temporary files
- Automatically cleans up after sending

### Data Storage
- SQLite database for play history
- Stores user feedback for model training
- Tracks listening patterns and preferences

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details. 