#!/usr/bin/env python3

"""
Step A: YouTube Video Ranker (Batch Processing Version)

This script loads a large dataset in chunks, ranks videos
based on semantic similarity to a live user intent, and saves
the ranked results to a new CSV.
"""

import csv
import math
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict

#
# NEW: This function processes the dataset in chunks to save memory
#
def rank_videos_from_file(user_intent: str, model: SentenceTransformer, filepath: str, chunk_size: int = 512) -> List[Dict[str, any]]:
    """
    Ranks videos from a CSV file against a user intent using batch processing.

    This method is memory-efficient, as it does not load the entire
    dataset into memory at once.

    Args:
        user_intent: The user's query string.
        model: A pre-loaded SentenceTransformer model.
        filepath: Path to the input CSV (must have 'title', 'transcript').
        chunk_size: How many videos to process in a single batch.
    
    Returns:
        A list of dictionaries, sorted by 'score' in descending order.
    """
    
    # 1. Embed the user intent ONCE
    print("Embedding user intent...")
    intent_embedding = model.encode(user_intent, convert_to_tensor=True)

    all_results = []
    
    try:
        with open(filepath, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            chunk_videos = []
            batch_num = 1
            
            print(f"Starting batch processing (chunk size: {chunk_size})...")
            
            # Loop through every row in the large CSV
            for row in reader:
                if 'title' in row and 'transcript' in row:
                    chunk_videos.append(row)
                
                # When the chunk is full, process it
                if len(chunk_videos) >= chunk_size:
                    process_chunk(chunk_videos, intent_embedding, model, all_results)
                    print(f"Processed batch {batch_num} ({len(all_results)} videos ranked so far)")
                    batch_num += 1
                    chunk_videos = [] # Reset the chunk

            # Process any remaining videos (the last, smaller chunk)
            if chunk_videos:
                process_chunk(chunk_videos, intent_embedding, model, all_results)
                print(f"Processed final batch {batch_num} ({len(all_results)} total videos ranked)")
            
            if not all_results:
                print("Warning: No valid videos found in the dataset.")
                return []

            # 3. Sort the final combined results
            # This is the only part that uses more memory, but a list of
            # scores/titles is much smaller than all embeddings.
            print("All batches processed. Sorting final results...")
            ranked_results = sorted(all_results, key=lambda x: x['score'], reverse=True)
            return ranked_results

    except FileNotFoundError:
        print(f"Error: Dataset file not found at {filepath}")
        return []
    except Exception as e:
        print(f"Error reading or processing file: {e}")
        return []

def process_chunk(chunk_videos: List[Dict], intent_embedding, model, all_results: List):
    """
    Helper function to encode and score a single chunk of videos.
    (Results are appended to the 'all_results' list in-place)
    """
    # 2. Combine and Embed the video chunk
    video_texts = [f"{video['title']}. {video['transcript']}" for video in chunk_videos]
    
    # show_progress_bar=True is useful for large chunks
    video_embeddings = model.encode(video_texts, convert_to_tensor=True, show_progress_bar=False)

    # 3. Compute cosine similarity
    cosine_scores = util.cos_sim(intent_embedding, video_embeddings)

    # 4. Store chunk results
    for i, video in enumerate(chunk_videos):
        # Create a new dict with the original data + the score
        ranked_item = video.copy() 
        ranked_item['score'] = cosine_scores[0][i].item()
        all_results.append(ranked_item)

#
# This function is unchanged but still very useful.
#
def save_results_to_csv(results: List[Dict[str, any]], filepath: str):
    """Saves the ranked results (with scores) to a new CSV file."""
    if not results:
        print("No results to save.")
        return

    print(f"Saving {len(results)} ranked results to {filepath}...")
    
    # Get all column headers from the first result item
    fieldnames = results[0].keys()
    
    with open(filepath, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print("Results saved successfully.")


# --- Main Execution ---

def main():
    """
    Main function to load, rank, and save the video data.
    """
    
    # --- Configuration ---
    DATASET_FILE = "videos.csv"
    RESULTS_FILE = "ranked_results.csv"
    MODEL_NAME = "./my-finetuned-model"
    BATCH_SIZE = 512  # Tune this based on your RAM/VRAM. 512 is a good start.
    # --- End Configuration ---
    
    # 1. GET LIVE USER INPUT
    user_intent = input("What would you like to focus on? ")
    print(f"Got it. Searching for: '{user_intent}'")

    # 2. Load the model
    print(f"Loading sentence-transformer model '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)
    print("Model loaded successfully.")
    
    # 3. Run the ranking (using the new batch-processing function)
    ranked_list = rank_videos_from_file(
        user_intent, 
        model, 
        DATASET_FILE, 
        chunk_size=BATCH_SIZE
    )
    
    if not ranked_list:
        print("Ranking failed or no results found. Exiting.")
        return

    # 4. Print top 5 results to console
    print("\n" + "="*30)
    print(f"User Intent: '{user_intent}'")
    print("\nTop 5 Ranked Video Results:")
    for item in ranked_list:
        print(f"{item['score']:.2f} → {item['title']}")
        
    # 5. Save all results to the output CSV
    save_results_to_csv(ranked_list, RESULTS_FILE)

if __name__ == "__main__":
    main()