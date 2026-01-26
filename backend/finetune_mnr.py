#!/usr/bin/env python3

"""
This script fine-tunes a model using MultipleNegativesRankingLoss (MNR).
It learns from a CSV of (query, positive_video_transcript) pairs.
"""

import csv
from sentence_transformers import SentenceTransformer, losses
from torch.utils.data import DataLoader
from sentence_transformers.readers import InputExample

# --- 1. Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2'
TRAIN_DATA_FILE = 'finetune_data.csv'
NEW_MODEL_PATH = './my-finetuned-model' # Folder to save the new model
BATCH_SIZE = 16
NUM_EPOCHS = 10  # <-- Give it 10 epochs to learn
LEARNING_RATE = 1e-5 # <-- Set a safe, low learning rate

# --- 2. Load the base model ---
print(f"Loading base model '{MODEL_NAME}'...")
model = SentenceTransformer(MODEL_NAME)

# --- 3. Load the training data ---
print(f"Loading training data from '{TRAIN_DATA_FILE}'...")
train_examples = []
try:
    with open(TRAIN_DATA_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'query' in row and 'positive' in row:
                # MNR expects (anchor, positive) pairs
                train_examples.append(InputExample(texts=[row['query'], row['positive']]))
            else:
                print("Warning: Skipping row with missing 'query' or 'positive' column.")
    
    if not train_examples:
        print("Error: No valid training data found. Exiting.")
        exit()
        
    print(f"Loaded {len(train_examples)} training pairs.")

except FileNotFoundError:
    print(f"Error: Training file not found at {TRAIN_DATA_FILE}")
    exit()

# --- 4. Define the Loss and DataLoader ---

# Create a DataLoader to batch the examples
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=BATCH_SIZE)

# Define the loss function: MultipleNegativesRankingLoss
# This is the "magic" that makes it work. It takes a batch of (anchor, positive)
# pairs and treats all other positives in the batch as "negatives" for
# a given anchor.
train_loss = losses.MultipleNegativesRankingLoss(model)

# --- 5. Run the Training ---
print("Starting fine-tuning...")

# 10% of training steps for warmup
warmup_steps = int(len(train_dataloader) * NUM_EPOCHS * 0.1) 

# Calculate warmup steps based on total steps
total_steps = len(train_dataloader) * NUM_EPOCHS
warmup_steps = int(total_steps * 0.1) # 10% of total steps

model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=NUM_EPOCHS,
    warmup_steps=warmup_steps,
    output_path=NEW_MODEL_PATH,
    show_progress_bar=True,
    # --- ADD THIS PARAMETER ---
    optimizer_params={'lr': LEARNING_RATE}
)
print(f"Fine-tuning complete. Model saved to '{NEW_MODEL_PATH}'")

# --- 6. How to use it ---
print("\nTo use your new model in your ranking script:")
print(f"1. Open your 'video_ranker_batch.py' script.")
print(f"2. Change the 'MODEL_NAME' variable from '{MODEL_NAME}' to '{NEW_MODEL_PATH}'")