#!/usr/bin/env python3

"""
Offline Pre-processing Script (Step 1)

This script loads a CLIP model to create and save image embeddings
for all video thumbnails listed in the videos.csv file.

This only needs to be run ONCE, or whenever new videos are added.
"""

import csv
import numpy as np
from sentence_transformers import SentenceTransformer
from PIL import Image
from typing import List, Dict

# --- Configuration ---
CLIP_MODEL_NAME = 'clip-ViT-B-32'
VIDEO_DATA_FILE = 'videos.csv'
OUTPUT_EMBEDDINGS_FILE = 'video_image_embeddings.npy' # The final output file

def load_video_data(filepath: str) -> List[Dict[str, str]]:
    """Loads the CSV and finds all thumbnail paths."""
    videos = []
    print(f"Loading dataset from {filepath}...")
    try:
        with open(filepath, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'thumbnail_path' in row and row['thumbnail_path']:
                    videos.append(row)
                else:
                    print(f"Skipping row (missing 'thumbnail_path'): {row['title']}")
        return videos
    except FileNotFoundError:
        print(f"Error: Dataset file not found at {filepath}")
        return []

def main():
    # 1. Load the CLIP model
    # This model can embed BOTH text and images
    print(f"Loading CLIP model '{CLIP_MODEL_NAME}'...")
    model = SentenceTransformer(CLIP_MODEL_NAME)
    print("Model loaded successfully.")

    # 2. Load video data from CSV
    videos = load_video_data(VIDEO_DATA_FILE)
    if not videos:
        print("No videos found. Exiting.")
        return

    # 3. Create a list of image paths to process
    image_paths = [video['thumbnail_path'] for video in videos]
    print(f"Found {len(image_paths)} images to embed.")

    # 4. Open all images using PIL
    # model.encode() for images requires a list of PIL Image objects
    pil_images = []
    for path in image_paths:
        try:
            # 
            img = Image.open(path)
            pil_images.append(img)
        except FileNotFoundError:
            print(f"Error: Image not found at {path}. Skipping.")
            # We add a placeholder 'None' to keep the list aligned
            pil_images.append(None) 
        except Exception as e:
            print(f"Error opening {path}: {e}")
            pil_images.append(None)

    # Filter out any images that failed to load
    # We must also filter the 'videos' list to keep them in sync
    valid_images = [img for img in pil_images if img is not None]
    
    # This is a bit advanced, but it syncs the 'videos' list
    # with the 'valid_images' list
    synced_videos = [video for video, img in zip(videos, pil_images) if img is not None]
    
    if len(valid_images) != len(videos):
        print(f"Warning: Could only process {len(valid_images)} out of {len(videos)} images.")

    if not valid_images:
        print("No valid images could be loaded. Exiting.")
        return

    # 5. Encode all images in a single batch (fast!)
    print(f"Embedding {len(valid_images)} images...")
    
    # The 'encode' function is smart. If you give it text, it embeds text.
    # If you give it a PIL Image, it embeds the image.
    image_embeddings = model.encode(valid_images, batch_size=32, show_progress_bar=True)

    # 6. Save the embeddings to a file
    # We also save the titles in order, just as a sanity check
    # The .npy file is a fast, efficient way to save a list of vectors
    print(f"Saving embeddings to {OUTPUT_EMBEDDINGS_FILE}...")
    np.save(OUTPUT_EMBEDDINGS_FILE, image_embeddings)
    
    # As a helper, let's also save the *order* of the videos we embedded
    # This makes it easier to load them in the main script
    with open('video_order.txt', 'w', encoding='utf-8') as f:
        for video in synced_videos:
            f.write(f"{video['title']}\n")

    print("\nPre-processing complete!")
    print(f"Image vectors saved to: {OUTPUT_EMBEDDINGS_FILE}")
    print(f"Video order saved to: video_order.txt")

if __name__ == "__main__":
    main()