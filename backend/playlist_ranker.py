"""
Multimodal Playlist Video Ranker (FIXED VERSION)

This module integrates YouTube playlist fetching with multimodal ranking.
It takes a YouTube playlist URL and user intent, then ranks videos based on
combined text and visual embeddings.

IMPROVEMENTS:
1. Uses YouTube CDN URL pattern for guaranteed thumbnail access
2. Batch encodes images for consistent embedding dimensions
3. Gracefully handles failed thumbnails without corrupting rankings
4. Validates embedding shapes before tensor conversion
"""

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from PIL import Image
from typing import List, Dict, Optional, Tuple
from io import BytesIO
import requests
import logging
import os
from pathlib import Path

from playlist_parser import PlaylistParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
BASE_DIR = Path(__file__).parent
LOCAL_TEXT_MODEL = BASE_DIR / "my-finetuned-model"
TEXT_MODEL_NAME = os.getenv(
    "TEXT_MODEL_NAME",
    str(LOCAL_TEXT_MODEL) if LOCAL_TEXT_MODEL.exists() else "all-MiniLM-L6-v2"
)
VISUAL_MODEL_NAME = os.getenv("VISUAL_MODEL_NAME", "clip-ViT-B-32")
TEXT_WEIGHT = 0.7
VISUAL_WEIGHT = 0.3
EXPECTED_EMBEDDING_DIM = 512  # CLIP embeddings dimension

# Cache for downloaded thumbnails and embeddings
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


class PlaylistRanker:
    """
    Ranks videos from a YouTube playlist based on multimodal embeddings.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the PlaylistRanker.
        
        Args:
            api_key: YouTube API key. If None, uses environment variable.
        """
        logger.info("Initializing PlaylistRanker...")
        
        # Initialize parser
        self.parser = PlaylistParser(api_key=api_key)
        
        # Load models
        logger.info(f"Loading text model: {TEXT_MODEL_NAME}")
        self.text_model = SentenceTransformer(TEXT_MODEL_NAME)
        
        logger.info(f"Loading visual model: {VISUAL_MODEL_NAME}")
        self.visual_model = SentenceTransformer(VISUAL_MODEL_NAME)
        
        logger.info("PlaylistRanker initialized successfully")
    
    def _get_youtube_thumbnail_url(self, video_id: str, quality: str = "hqdefault") -> str:
        """
        Generate YouTube CDN thumbnail URL for a video.
        This is guaranteed to work for any valid video ID.
        
        Quality options:
        - 'default': 120x90
        - 'hqdefault': 480x360 (recommended)
        - 'maxresdefault': 1280x720 (may not exist for all videos)
        
        Args:
            video_id: YouTube video ID
            quality: Thumbnail quality
            
        Returns:
            URL string for the thumbnail
        """
        return f"https://i.ytimg.com/vi/{video_id}/{quality}.jpg"
    
    def _download_thumbnail(self, video_id: str, thumbnail_url: str) -> Optional[Image.Image]:
        """
        Download a thumbnail from URL and return as PIL Image.
        
        Args:
            video_id: YouTube video ID
            thumbnail_url: URL of the thumbnail
            
        Returns:
            PIL Image object (RGB), or None if failed
        """
        try:
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()
            
            image = Image.open(BytesIO(response.content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return image
        
        except Exception as e:
            logger.debug(f"Failed to download thumbnail for {video_id}: {e}")
            return None
    
    def _get_text_representation(self, video: Dict) -> str:
        """
        Create a text representation of the video for embedding.
        
        Args:
            video: Video metadata dictionary
            
        Returns:
            Combined text string for the video
        """
        title = video.get('title', '')
        description = video.get('description', '')
        
        # Repeat title for emphasis (weighted towards title)
        text = f"{title} {title} {description}"
        return text.strip()
    
    def rank_playlist(self, playlist_url: str, user_intent: str) -> List[Dict]:
        """
        Fetch a playlist and rank its videos based on user intent.
        
        Args:
            playlist_url: YouTube playlist URL
            user_intent: Natural language description of what the user wants
            
        Returns:
            List of ranked videos with scores and metadata
        """
        logger.info(f"Starting playlist ranking for intent: '{user_intent}'")
        
        # Step 1: Fetch playlist videos
        logger.info("Fetching playlist videos...")
        videos = self.parser.fetch_playlist_videos(playlist_url, use_cache=True)
        
        if not videos:
            logger.error("No videos found in playlist")
            return []
        
        logger.info(f"Found {len(videos)} videos in playlist")
        
        # Step 2: Generate text embeddings for all videos
        logger.info("Generating text embeddings...")
        video_texts = [self._get_text_representation(v) for v in videos]
        text_embeddings = self.text_model.encode(video_texts, convert_to_tensor=True)
        
        # Step 3: Download thumbnails (batch process)
        logger.info("Downloading thumbnails...")
        thumbnail_images = []
        valid_visual_indices = []  # Track which videos have valid thumbnails
        
        for idx, video in enumerate(videos):
            video_id = video['video_id']
            thumbnail_url = self._get_youtube_thumbnail_url(video_id, quality="hqdefault")
            
            image = self._download_thumbnail(video_id, thumbnail_url)
            if image is not None:
                thumbnail_images.append(image)
                valid_visual_indices.append(idx)
            else:
                logger.warning(f"Could not download thumbnail for {video['title']}")
        
        logger.info(f"Successfully downloaded {len(thumbnail_images)} out of {len(videos)} thumbnails")
        
        # Step 4: Batch encode all thumbnails (ensures consistent dimensions)
        logger.info("Generating visual embeddings (batch processing)...")
        if thumbnail_images:
            visual_embeddings_raw = self.visual_model.encode(
                thumbnail_images,
                convert_to_tensor=False
            )

            # Normalize embeddings to a list of 1D arrays
            if isinstance(visual_embeddings_raw, np.ndarray) and visual_embeddings_raw.dtype != object and visual_embeddings_raw.ndim == 2:
                embeddings_list = [row for row in visual_embeddings_raw]
            else:
                embeddings_list = list(visual_embeddings_raw)

            # Filter out malformed embeddings and align indices
            filtered_embeddings = []
            filtered_indices = []
            for idx, emb in zip(valid_visual_indices, embeddings_list):
                emb_arr = np.asarray(emb)
                if emb_arr.ndim == 1 and emb_arr.shape[0] == EXPECTED_EMBEDDING_DIM:
                    filtered_embeddings.append(emb_arr)
                    filtered_indices.append(idx)
                else:
                    logger.warning(f"Dropping malformed visual embedding for video index {idx}: shape={getattr(emb_arr, 'shape', None)}")

            if filtered_embeddings:
                visual_embeddings_batch = np.vstack(filtered_embeddings)
                valid_visual_indices = filtered_indices
                logger.info(f"Visual embeddings shape: {visual_embeddings_batch.shape}")
                if visual_embeddings_batch.shape[1] != EXPECTED_EMBEDDING_DIM:
                    logger.warning(f"Expected embedding dim {EXPECTED_EMBEDDING_DIM}, got {visual_embeddings_batch.shape[1]}")
            else:
                logger.warning("No valid visual embeddings after filtering, will use text-only ranking")
                visual_embeddings_batch = None
        else:
            logger.warning("No valid visual embeddings available, will use text-only ranking")
            visual_embeddings_batch = None
        
        # Step 5: Encode user intent with both models
        logger.info("Encoding user intent...")
        text_intent = self.text_model.encode(user_intent, convert_to_tensor=True)
        visual_intent = self.visual_model.encode(user_intent, convert_to_tensor=True) if visual_embeddings_batch is not None else None
        
        # Step 6: Calculate similarity scores
        logger.info("Calculating similarity scores...")
        text_scores = util.cos_sim(text_intent, text_embeddings)[0]
        
        # Calculate visual scores only for videos with valid embeddings
        if visual_embeddings_batch is not None:
            visual_embeddings_tensor = torch.from_numpy(visual_embeddings_batch).to(text_embeddings.device)
            visual_scores_valid = util.cos_sim(visual_intent, visual_embeddings_tensor)[0]
        else:
            visual_scores_valid = None
        
        # Step 7: Combine scores and create results
        results = []
        for i, video in enumerate(videos):
            text_score = text_scores[i].item()
            
            # Check if this video has a visual embedding
            if visual_scores_valid is not None and i in valid_visual_indices:
                # Get the visual score from the valid embeddings list
                visual_idx = valid_visual_indices.index(i)
                visual_score = visual_scores_valid[visual_idx].item()
                # Full weighted combination
                final_score = (TEXT_WEIGHT * text_score) + (VISUAL_WEIGHT * visual_score)
            else:
                # No visual embedding: use only text score
                visual_score = 0.0
                final_score = text_score  # Text becomes the full score
                logger.debug(f"Using text-only score for: {video['title']}")
            
            results.append({
                'video_id': video['video_id'],
                'title': video['title'],
                'description': video['description'],
                'thumbnail_url': self._get_youtube_thumbnail_url(video['video_id'], quality="default"),
                'thumbnail_url_hq': self._get_youtube_thumbnail_url(video['video_id'], quality="hqdefault"),
                'thumbnail_url_max': self._get_youtube_thumbnail_url(video['video_id'], quality="maxresdefault"),
                'published_at': video.get('published_at'),
                'final_score': final_score,
                'text_score': text_score,
                'visual_score': visual_score,
                'has_visual_embedding': i in valid_visual_indices,
                'youtube_url': f"https://www.youtube.com/watch?v={video['video_id']}"
            })
        
        # Step 8: Sort by final score
        ranked_results = sorted(results, key=lambda x: x['final_score'], reverse=True)
        
        logger.info(f"Ranking complete. Top video: {ranked_results[0]['title']} (score: {ranked_results[0]['final_score']:.4f})")
        logger.info(f"Videos with visual embeddings: {sum(1 for v in ranked_results if v['has_visual_embedding'])}")
        
        return ranked_results
    
    def rank_playlist_filtered(self, playlist_url: str, user_intent: str, min_score: float = 0.10) -> List[Dict]:
        """
        Rank a playlist and filter results by minimum score.
        
        Args:
            playlist_url: YouTube playlist URL
            user_intent: Natural language description of what the user wants
            min_score: Minimum relevance score to include (0.0 to 1.0)
            
        Returns:
            List of ranked videos with score >= min_score
        """
        ranked = self.rank_playlist(playlist_url, user_intent)
        filtered = [v for v in ranked if v['final_score'] >= min_score]
        
        logger.info(f"Filtered {len(ranked)} videos to {len(filtered)} with score >= {min_score}")
        
        return filtered


# Example usage and testing
if __name__ == "__main__":
    import os
    
    # Check if API key is set
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("ERROR: YouTube API key not set!")
        print("Set the YOUTUBE_API_KEY environment variable:")
        print("  export YOUTUBE_API_KEY='your_api_key_here'")
        exit(1)
    
    # Initialize ranker
    print("\n--- Initializing PlaylistRanker ---")
    ranker = PlaylistRanker(api_key=api_key)
    
    # Get user input
    print("\n--- Playlist Video Ranking ---")
    playlist_url = input("Enter a YouTube playlist URL: ").strip()
    user_intent = input("What would you like to focus on? (e.g., 'learn linear algebra'): ").strip()
    
    if playlist_url and user_intent:
        # Rank the playlist
        print("\nRanking videos... This may take a moment.")
        ranked_videos = ranker.rank_playlist(playlist_url, user_intent)
        
        # Display results
        print(f"\n--- Ranked Results (Top 10) ---")
        for i, video in enumerate(ranked_videos[:10], 1):
            visual_status = "✓" if video['has_visual_embedding'] else "○"
            print(f"\n{i}. {video['title']} [{visual_status}]")
            print(f"   Final Score: {video['final_score']:.4f}")
            print(f"   Text Score: {video['text_score']:.4f} | Visual Score: {video['visual_score']:.4f}")
            print(f"   Watch: {video['youtube_url']}")
