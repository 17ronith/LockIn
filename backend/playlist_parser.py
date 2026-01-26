"""
YouTube Data API Integration Module

This module handles:
1. Fetching playlist metadata and video details from YouTube
2. Extracting video transcripts using youtube-transcript-api
3. Caching fetched data locally to avoid redundant API calls
"""

import os
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import logging
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# YouTube Thumbnail URL Template
# Available qualities: default, mqdefault, sddefault, hqdefault, maxresdefault
YOUTUBE_THUMBNAIL_URL_TEMPLATE = "https://i.ytimg.com/vi/{video_id}/{quality}.jpg"
THUMBNAIL_QUALITY = "hqdefault"  # Use high quality thumbnails (480x360)

# API Key - Get this from Google Cloud Console
# Set as environment variable: export YOUTUBE_API_KEY="your_key_here"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", None)


class PlaylistParser:
    """
    Handles fetching and caching YouTube playlist metadata and transcripts.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the PlaylistParser with a YouTube API key.
        
        Args:
            api_key: YouTube API key. If None, will use YOUTUBE_API_KEY environment variable.
        
        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or YOUTUBE_API_KEY
        if not self.api_key:
            raise ValueError(
                "YouTube API key not provided. Set YOUTUBE_API_KEY environment variable or pass it directly."
            )
        self.cache_dir = CACHE_DIR
        logger.info("PlaylistParser initialized")
    
    def _get_playlist_id_from_url(self, url: str) -> str:
        """
        Extract playlist ID from YouTube URL.
        
        Args:
            url: YouTube playlist URL
            
        Returns:
            Playlist ID
            
        Raises:
            ValueError: If URL is invalid
        """
        if not url:
            raise ValueError("Invalid YouTube playlist URL: empty")

        # Handle various YouTube playlist URL formats
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if "list" in query and query["list"]:
            return query["list"][0]

        if "list=" in url:
            return url.split("list=")[1].split("&")[0]

        # Allow direct playlist ID input
        if len(url) >= 10 and all(c.isalnum() or c in "-_" for c in url):
            return url

        raise ValueError(f"Invalid YouTube playlist URL: {url}")
    
    def _get_video_id_from_url(self, url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID
        """
        if "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        elif "youtube.com/watch?v=" in url:
            return url.split("v=")[1].split("&")[0]
        elif len(url) == 11:  # Direct video ID
            return url
        else:
            raise ValueError(f"Invalid YouTube video URL: {url}")
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Get the cache file path for a given cache key.
        
        Args:
            cache_key: Identifier for the cached item (e.g., playlist_id, video_id)
            
        Returns:
            Path object for the cache file
        """
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """
        Load data from local cache.
        
        Args:
            cache_key: Identifier for the cached item
            
        Returns:
            Cached data if available, None otherwise
        """
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                logger.info(f"Loaded from cache: {cache_key}")
                return data
            except Exception as e:
                logger.warning(f"Error loading cache for {cache_key}: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict) -> None:
        """
        Save data to local cache.
        
        Args:
            cache_key: Identifier for the cached item
            data: Data to cache
        """
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved to cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Error saving cache for {cache_key}: {e}")
    
    def fetch_playlist_videos(self, playlist_url: str, use_cache: bool = True) -> List[Dict]:
        """
        Fetch all videos from a YouTube playlist.
        
        Args:
            playlist_url: URL of the YouTube playlist
            use_cache: Whether to use cached data if available
            
        Returns:
            List of video dictionaries with metadata and thumbnail URLs
        """
        try:
            playlist_id = self._get_playlist_id_from_url(playlist_url)
        except ValueError as e:
            logger.error(str(e))
            return []
        
        cache_key = f"playlist_{playlist_id}"
        
        # Check cache first
        if use_cache:
            cached_data = self._load_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        videos = []
        next_page_token = None
        
        try:
            # Fetch videos from playlist using batch requests (up to 50 per request)
            session = requests.Session()
            while True:
                params = {
                    "part": "snippet,contentDetails",
                    "playlistId": playlist_id,
                    "maxResults": 50,
                    "key": self.api_key,
                    "fields": "nextPageToken,items(contentDetails/videoId,snippet/title,snippet/description,snippet/publishedAt,snippet/thumbnails)"
                }
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                response = session.get(f"{YOUTUBE_API_BASE_URL}/playlistItems", params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Process each video in the response
                for item in data.get("items", []):
                    snippet = item.get("snippet") or {}
                    content = item.get("contentDetails") or {}
                    video_id = content.get("videoId")

                    if not video_id:
                        logger.warning("Skipping item without videoId")
                        continue

                    title = snippet.get("title", "")
                    description = snippet.get("description", "")
                    published_at = snippet.get("publishedAt")

                    thumbnails = snippet.get("thumbnails") or {}
                    thumb = thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default")
                    thumb_url = thumb.get("url") if thumb else ""

                    # Generate thumbnail URLs (using high quality)
                    thumbnail_url_hq = self.get_thumbnail_url(video_id, quality="hqdefault")
                    thumbnail_url_max = self.get_thumbnail_url(video_id, quality="maxresdefault")

                    videos.append({
                        "video_id": video_id,
                        "title": title,
                        "description": description,
                        "thumbnail_url": thumb_url or thumbnail_url_hq,
                        "thumbnail_url_hq": thumbnail_url_hq,  # High quality (480x360)
                        "thumbnail_url_max": thumbnail_url_max,  # Max quality (1280x720)
                        "published_at": published_at,
                    })
                
                # Check for next page
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break
            
            logger.info(f"Fetched {len(videos)} videos from playlist {playlist_id}")
            
            # Cache the results
            if use_cache:
                self._save_to_cache(cache_key, videos)
            
            return videos
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return []
    
    def fetch_video_details(self, video_id: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Fetch detailed information about a specific video.
        
        Args:
            video_id: YouTube video ID
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary with video details, or None if failed
        """
        cache_key = f"video_{video_id}"
        
        # Check cache first
        if use_cache:
            cached_data = self._load_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        try:
            params = {
                "part": "snippet,contentDetails,statistics",
                "id": video_id,
                "key": self.api_key,
            }
            
            response = requests.get(f"{YOUTUBE_API_BASE_URL}/videos", params=params)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("items"):
                logger.warning(f"No details found for video {video_id}")
                return None
            
            item = data["items"][0]
            video_details = {
                "video_id": video_id,
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "channel_id": item["snippet"]["channelId"],
                "channel_title": item["snippet"]["channelTitle"],
                "published_at": item["snippet"]["publishedAt"],
                "thumbnail_url": item["snippet"]["thumbnails"]["default"]["url"],
                "duration": item["contentDetails"]["duration"],
                "view_count": int(item["statistics"].get("viewCount", 0)),
                "like_count": int(item["statistics"].get("likeCount", 0)),
                "comment_count": int(item["statistics"].get("commentCount", 0)),
            }
            
            # Cache the results
            if use_cache:
                self._save_to_cache(cache_key, video_details)
            
            return video_details
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch video details for {video_id}: {e}")
            return None
    
    def get_thumbnail_url(self, video_id: str, quality: str = THUMBNAIL_QUALITY) -> str:
        """
        Generate the YouTube thumbnail URL for a video.
        
        Args:
            video_id: YouTube video ID
            quality: Thumbnail quality (default, mqdefault, sddefault, hqdefault, maxresdefault)
                    - default: 120x90
                    - mqdefault: 320x180
                    - sddefault: 640x480
                    - hqdefault: 480x360 (recommended)
                    - maxresdefault: 1280x720 (may not be available)
            
        Returns:
            URL to the thumbnail image
        """
        return YOUTUBE_THUMBNAIL_URL_TEMPLATE.format(video_id=video_id, quality=quality)
    
    def clear_cache(self, cache_key: Optional[str] = None) -> None:
        """
        Clear cached data.
        
        Args:
            cache_key: Specific cache key to clear. If None, clears all cache.
        """
        if cache_key:
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cleared cache: {cache_key}")
        else:
            # Clear all cache
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared all cache")


# Example usage and testing
if __name__ == "__main__":
    # Check if API key is set
    if not YOUTUBE_API_KEY:
        print("ERROR: YouTube API key not set!")
        print("Set the YOUTUBE_API_KEY environment variable:")
        print("  export YOUTUBE_API_KEY='your_api_key_here'")
        exit(1)
    
    # Initialize parser
    parser = PlaylistParser()
    
    # Example: Fetch videos from a playlist
    print("\n--- Example: Fetch Playlist Videos ---")
    playlist_url = input("Enter a YouTube playlist URL: ").strip()
    
    if playlist_url:
        videos = parser.fetch_playlist_videos(playlist_url)
        print(f"\nFound {len(videos)} videos:")
        for i, video in enumerate(videos[:5], 1):  # Show first 5
            print(f"{i}. {video['title']}")
            print(f"   Thumbnail URL (HQ): {video['thumbnail_url_hq']}")
        
        print(f"\nThumbnail URLs are served directly from YouTube's CDN")
