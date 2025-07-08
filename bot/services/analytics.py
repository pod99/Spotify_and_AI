"""
Analytics service for generating charts
"""

import logging
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any
import os
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for generating analytics charts"""
    
    def __init__(self):
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def generate_chart(self, chart_type: str, user_data: Dict, user_id: int) -> str:
        """Generate chart based on type and user data"""
        try:
            # Map callback data to chart types
            if chart_type == "analytics_top_tracks" or chart_type == "popular_tracks":
                return await self._generate_popular_tracks_chart(user_data, user_id)
            elif chart_type == "analytics_top_artists" or chart_type == "popular_artists":
                return await self._generate_popular_artists_chart(user_data, user_id)
            elif chart_type == "analytics_activity" or chart_type == "activity_by_hour":
                return await self._generate_activity_by_hour_chart(user_data, user_id)
            elif chart_type == "activity_by_day":
                return await self._generate_activity_by_day_chart(user_data, user_id)
            elif chart_type == "analytics_years" or chart_type == "release_years":
                return await self._generate_release_years_chart(user_data, user_id)
            elif chart_type == "analytics_genres" or chart_type == "top_genre":
                return await self._generate_top_genre_chart(user_data, user_id)
            else:
                logger.warning(f"Unknown chart type: {chart_type}, generating error chart")
                return await self._generate_error_chart(f"Unknown chart type: {chart_type}")
                
        except Exception as e:
            logger.error(f"Error generating chart {chart_type}: {e}")
            return await self._generate_error_chart()
    
    async def _generate_popular_tracks_chart(self, user_data: Dict, user_id: int) -> str:
        """Generate popular tracks chart"""
        tracks = user_data.get('top_tracks', [])
        
        if not tracks:
            return await self._generate_error_chart("No track data available")
        
        # Get top 10 tracks
        top_tracks = tracks[:10]
        track_names = [track['name'][:20] + "..." if len(track['name']) > 20 else track['name'] for track in top_tracks]
        popularity = [track.get('popularity', 0) for track in top_tracks]
        
        # Create plotly chart
        fig = go.Figure(data=[
            go.Bar(
                x=track_names,
                y=popularity,
                marker_color='#1DB954',
                text=popularity,
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title="Your Most Popular Tracks",
            xaxis_title="Track",
            yaxis_title="Popularity Score",
            template="plotly_white",
            height=500
        )
        
        return await self._save_chart(fig, f"popular_tracks_{user_id}")
    
    async def _generate_popular_artists_chart(self, user_data: Dict, user_id: int) -> str:
        """Generate popular artists chart"""
        tracks = user_data.get('top_tracks', [])
        
        if not tracks:
            return await self._generate_error_chart("No track data available")
        
        # Count artist appearances
        artist_counts = {}
        for track in tracks:
            for artist in track.get('artists', []):
                artist_name = artist['name']
                artist_counts[artist_name] = artist_counts.get(artist_name, 0) + 1
        
        # Get top 10 artists
        top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        artist_names = [name[:20] + "..." if len(name) > 20 else name for name, _ in top_artists]
        counts = [count for _, count in top_artists]
        
        # Create plotly chart
        fig = go.Figure(data=[
            go.Bar(
                x=artist_names,
                y=counts,
                marker_color='#FF6B6B',
                text=counts,
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title="Your Most Listened Artists",
            xaxis_title="Artist",
            yaxis_title="Number of Tracks",
            template="plotly_white",
            height=500
        )
        
        return await self._save_chart(fig, f"popular_artists_{user_id}")
    
    async def _generate_activity_by_hour_chart(self, user_data: Dict, user_id: int) -> str:
        """Generate activity by hour chart"""
        # Simulate hourly activity data (in real implementation, this would come from history)
        hours = list(range(24))
        activity = [0] * 24
        
        # Add some simulated activity peaks
        activity[8] = 15   # Morning
        activity[12] = 25  # Lunch
        activity[18] = 30  # Evening
        activity[22] = 20  # Night
        
        # Create plotly chart
        fig = go.Figure(data=[
            go.Scatter(
                x=hours,
                y=activity,
                mode='lines+markers',
                line=dict(color='#4ECDC4', width=3),
                marker=dict(size=8)
            )
        ])
        
        fig.update_layout(
            title="Listening Activity by Hour",
            xaxis_title="Hour of Day",
            yaxis_title="Number of Plays",
            template="plotly_white",
            height=400,
            xaxis=dict(tickmode='linear', tick0=0, dtick=2)
        )
        
        return await self._save_chart(fig, f"activity_by_hour_{user_id}")
    
    async def _generate_activity_by_day_chart(self, user_data: Dict, user_id: int) -> str:
        """Generate activity by day chart"""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Simulate daily activity data
        activity = [25, 30, 28, 35, 40, 45, 35]  # Weekend peaks
        
        # Create plotly chart
        fig = go.Figure(data=[
            go.Bar(
                x=days,
                y=activity,
                marker_color='#45B7D1',
                text=activity,
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title="Listening Activity by Day",
            xaxis_title="Day of Week",
            yaxis_title="Number of Plays",
            template="plotly_white",
            height=400
        )
        
        return await self._save_chart(fig, f"activity_by_day_{user_id}")
    
    async def _generate_release_years_chart(self, user_data: Dict, user_id: int) -> str:
        """Generate release years distribution chart"""
        tracks = user_data.get('top_tracks', [])
        
        if not tracks:
            return await self._generate_error_chart("No track data available")
        
        # Extract release years
        years = []
        for track in tracks:
            album = track.get('album', {})
            release_date = album.get('release_date', '')
            if release_date and len(release_date) >= 4:
                try:
                    year = int(release_date[:4])
                    if 1900 <= year <= 2024:
                        years.append(year)
                except ValueError:
                    continue
        
        if not years:
            return await self._generate_error_chart("No release year data available")
        
        # Count years
        year_counts = {}
        for year in years:
            year_counts[year] = year_counts.get(year, 0) + 1
        
        # Sort by year
        sorted_years = sorted(year_counts.items())
        years_list = [str(year) for year, _ in sorted_years]
        counts = [count for _, count in sorted_years]
        
        # Create plotly chart
        fig = go.Figure(data=[
            go.Bar(
                x=years_list,
                y=counts,
                marker_color='#96CEB4',
                text=counts,
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title="Release Years Distribution",
            xaxis_title="Release Year",
            yaxis_title="Number of Tracks",
            template="plotly_white",
            height=400
        )
        
        return await self._save_chart(fig, f"release_years_{user_id}")
    
    async def _generate_top_genre_chart(self, user_data: Dict, user_id: int) -> str:
        """Generate top genre chart"""
        tracks = user_data.get('top_tracks', [])
        
        if not tracks:
            return await self._generate_error_chart("No track data available")
        
        # Simulate genre data (in real implementation, this would come from track analysis)
        genres = ['Pop', 'Rock', 'Electronic', 'Hip Hop', 'R&B', 'Indie', 'Jazz', 'Classical']
        counts = [25, 20, 15, 12, 10, 8, 5, 3]
        
        # Create plotly pie chart
        fig = go.Figure(data=[
            go.Pie(
                labels=genres,
                values=counts,
                hole=0.3,
                marker_colors=px.colors.qualitative.Set3
            )
        ])
        
        fig.update_layout(
            title="Your Top Genres",
            template="plotly_white",
            height=500
        )
        
        return await self._save_chart(fig, f"top_genre_{user_id}")
    
    async def _generate_error_chart(self, message: str = "Error generating chart") -> str:
        """Generate error chart"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="red")
        )
        
        fig.update_layout(
            title="Chart Generation Error",
            template="plotly_white",
            height=300
        )
        
        return await self._save_chart(fig, "error_chart")
    
    async def _save_chart(self, fig, filename: str) -> str:
        """Save chart to temporary file"""
        try:
            filepath = os.path.join(self.temp_dir, f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            fig.write_image(filepath, width=800, height=600)
            return filepath
        except Exception as e:
            logger.error(f"Error saving chart: {e}")
            # Fallback to matplotlib
            return await self._save_matplotlib_chart(fig, filename)
    
    async def _save_matplotlib_chart(self, fig, filename: str) -> str:
        """Fallback to matplotlib for saving"""
        try:
            filepath = os.path.join(self.temp_dir, f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            # Convert plotly figure to matplotlib
            fig_bytes = fig.to_image(format="png")
            
            with open(filepath, 'wb') as f:
                f.write(fig_bytes)
            
            return filepath
        except Exception as e:
            logger.error(f"Error saving matplotlib chart: {e}")
            # Create a simple error image
            return await self._create_simple_error_image(filename)
    
    async def _create_simple_error_image(self, filename: str) -> str:
        """Create a simple error image using matplotlib"""
        try:
            filepath = os.path.join(self.temp_dir, f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            plt.figure(figsize=(8, 6))
            plt.text(0.5, 0.5, 'Chart Generation Error', 
                    ha='center', va='center', transform=plt.gca().transAxes,
                    fontsize=16, color='red')
            plt.axis('off')
            plt.savefig(filepath, bbox_inches='tight', dpi=100)
            plt.close()
            
            return filepath
        except Exception as e:
            logger.error(f"Error creating error image: {e}")
            return "" 