import csv
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
TEXT_MODEL_NAME = './my-finetuned-model'
VISUAL_MODEL_NAME = 'clip-ViT-B-32'
VIDEO_DATA_FILE = 'videos.csv'
IMAGE_EMBEDDINGS_FILE = 'video_image_embeddings.npy'
TEXT_WEIGHT = 0.7
VISUAL_WEIGHT = 0.3

# --- Pre-load all models and data --- //
# This code runs ONCE when the script is imported.
try:
    print("Loading models and data... (This may take a moment)")
    
    # Load models
    text_model = SentenceTransformer(TEXT_MODEL_NAME)
    visual_model = SentenceTransformer(VISUAL_MODEL_NAME)
    
    # Load video text data
    video_data = {}
    with open(VIDEO_DATA_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            video_data[row['title']] = {
                'transcript': row['transcript'],
                'thumbnail_path': row['thumbnail_path']
            }
            
    # Load image embeddings
    image_embeddings = np.load(IMAGE_EMBEDDINGS_FILE)
    
    # Load synced video order
    with open('video_order.txt', 'r', encoding='utf-8') as f:
        video_order = [line.strip() for line in f]
    
    # Create the final, synced list of video documents
    synced_videos = []
    for title in video_order:
        if title in video_data:
            synced_videos.append({
                'title': title,
                'transcript': video_data[title]['transcript']
            })
            
    # Pre-encode all video transcripts
    print("Pre-encoding video transcripts...")
    video_transcripts = [video['transcript'] for video in synced_videos]
    text_embeddings = text_model.encode(video_transcripts, convert_to_tensor=True)
    
    # Move image embeddings to the correct device
    device = text_embeddings.device
    image_embeddings_tensor = torch.from_numpy(image_embeddings).to(device)

    print("Models and data loaded successfully.")
    print("You can now run 'streamlit run app.py'")

except Exception as e:
    print(f"Error loading files: {e}")
    print("Please ensure all data files and models are present.")
    synced_videos = None # Flag that loading failed

# --- This is our main function for the app ---
def get_ranked_videos(user_intent: str) -> List[Dict]:
    if not synced_videos:
        return [] # Return empty if loading failed
        
    # 1. Encode Intent with BOTH models
    text_intent_vector = text_model.encode(user_intent, convert_to_tensor=True)
    visual_intent_vector = visual_model.encode(user_intent, convert_to_tensor=True)

    # 2. Calculate Scores
    text_scores = util.cos_sim(text_intent_vector, text_embeddings)[0]
    visual_scores = util.cos_sim(visual_intent_vector, image_embeddings_tensor)[0]

    # 3. Combine Scores and Rank
    results = []
    for i in range(len(synced_videos)):
        text_score = text_scores[i].item()
        visual_score = visual_scores[i].item()
        
        final_score = (TEXT_WEIGHT * text_score) + (VISUAL_WEIGHT * visual_score)
        
        results.append({
            'title': synced_videos[i]['title'],
            'final_score': final_score,
            'text_score': text_score,
            'visual_score': visual_score,
            'thumbnail_path': video_data[synced_videos[i]['title']]['thumbnail_path']
        })

    ranked_results = sorted(results, key=lambda x: x['final_score'], reverse=True)
    return ranked_results


# --- NEW: Function for ranking YouTube playlists ---
def rank_youtube_playlist(playlist_url: str, user_intent: str, api_key: Optional[str] = None) -> List[Dict]:
    """
    Rank videos from a YouTube playlist based on multimodal embeddings.
    
    This function:
    1. Fetches videos from the YouTube playlist
    2. Generates text embeddings from titles/descriptions
    3. Downloads thumbnails and generates visual embeddings
    4. Ranks videos based on user intent
    
    Args:
        playlist_url: YouTube playlist URL
        user_intent: Natural language description of what the user wants
        api_key: YouTube API key (optional, uses env var if not provided)
        
    Returns:
        List of ranked videos sorted by relevance score
    """
    from playlist_parser import PlaylistParser
    from PIL import Image
    from io import BytesIO
    import requests
    
    logger.info(f"Starting playlist ranking for: {playlist_url}")
    logger.info(f"User intent: {user_intent}")
    
    # Initialize playlist parser
    parser = PlaylistParser(api_key=api_key)
    
    # Fetch playlist videos
    logger.info("Fetching playlist videos...")
    videos = parser.fetch_playlist_videos(playlist_url, use_cache=True)
    
    if not videos:
        logger.error("No videos found in playlist")
        return []
    
    logger.info(f"Found {len(videos)} videos")
    
    # Generate text embeddings from titles and descriptions
    logger.info("Generating text embeddings...")
    video_texts = []
    for video in videos:
        # Combine title and description for better representation
        text = f"{video['title']} {video['title']} {video['description']}"
        video_texts.append(text)
    
    text_embeddings_playlist = text_model.encode(video_texts, convert_to_tensor=True)
    
    # Generate visual embeddings from thumbnails
    logger.info("Downloading thumbnails and generating visual embeddings...")
    visual_embeddings_list = []
    
    for video in videos:
        try:
            # Use high quality thumbnail
            thumbnail_url = video.get('thumbnail_url_hq', video.get('thumbnail_url'))
            
            # Download thumbnail
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()
            
            # Load as PIL image
            image = Image.open(BytesIO(response.content))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Generate embedding
            embedding = visual_model.encode(image, convert_to_tensor=False)
            visual_embeddings_list.append(embedding)
            
        except Exception as e:
            logger.warning(f"Failed to process thumbnail for {video['title']}: {e}")
            # Use zero vector as fallback
            embedding_dim = visual_model.get_sentence_embedding_dimension()
            visual_embeddings_list.append(np.zeros(embedding_dim))
    
    # Convert to tensor (ensure consistent shape)
    visual_embeddings_array = np.array(visual_embeddings_list)
    # Handle case where embeddings might have different shapes
    if len(visual_embeddings_array.shape) != 2:
        visual_embeddings_array = np.vstack(visual_embeddings_list)
    visual_embeddings_playlist = torch.from_numpy(visual_embeddings_array).to(text_embeddings_playlist.device)
    
    # Encode user intent
    logger.info("Encoding user intent...")
    text_intent = text_model.encode(user_intent, convert_to_tensor=True)
    visual_intent = visual_model.encode(user_intent, convert_to_tensor=True)
    
    # Calculate similarity scores
    logger.info("Calculating similarity scores...")
    text_scores = util.cos_sim(text_intent, text_embeddings_playlist)[0]
    visual_scores = util.cos_sim(visual_intent, visual_embeddings_playlist)[0]
    
    # Combine scores and rank
    results = []
    for i, video in enumerate(videos):
        text_score = text_scores[i].item()
        visual_score = visual_scores[i].item()
        
        final_score = (TEXT_WEIGHT * text_score) + (VISUAL_WEIGHT * visual_score)
        
        results.append({
            'video_id': video['video_id'],
            'title': video['title'],
            'description': video['description'],
            'final_score': final_score,
            'text_score': text_score,
            'visual_score': visual_score,
            'thumbnail_url': video.get('thumbnail_url'),
            'thumbnail_url_hq': video.get('thumbnail_url_hq'),
            'thumbnail_url_max': video.get('thumbnail_url_max'),
            'published_at': video.get('published_at'),
            'youtube_url': f"https://www.youtube.com/watch?v={video['video_id']}"
        })
    
    ranked_results = sorted(results, key=lambda x: x['final_score'], reverse=True)
    
    logger.info(f"Ranking complete. Top result: {ranked_results[0]['title']} (score: {ranked_results[0]['final_score']:.4f})")
    
    return ranked_results