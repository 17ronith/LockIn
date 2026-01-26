import uvicorn
import httpx
import torch
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # <-- 1. IMPORT THE FIX
from pydantic import BaseModel
from typing import List, Dict
from PIL import Image
import io
from sentence_transformers import SentenceTransformer, util

# --- Load Models Once at Startup ---
try:
    print("Loading models... (This may take a moment)")
    TEXT_MODEL_NAME = './my-finetuned-model'
    VISUAL_MODEL_NAME = 'clip-ViT-B-32'
    text_model = SentenceTransformer(TEXT_MODEL_NAME)
    visual_model = SentenceTransformer(VISUAL_MODEL_NAME)
    device = text_model.device
    print(f"Models loaded successfully on device: {device}")
except Exception as e:
    print(f"FATAL: Could not load models. API cannot start. Error: {e}")
    text_model = None
    visual_model = None

# --- Configuration ---
TEXT_WEIGHT = 0.7
VISUAL_WEIGHT = 0.3
MIN_SCORE = 0.01  # <-- I'VE LOWERED THE FILTER FOR TESTING

# --- API Setup ---
app = FastAPI(
    title="Multimodal Video Ranker API",
    description="Ranks video titles/thumbnails against a user intent."
)

# --- 2. ADD THE FIX ---
# Define which "origins" (websites) are allowed to talk to our API
origins = [
    "https://www.youtube.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST"],  # Only allow POST requests
    allow_headers=["*"],
)
# ---------------------

client = httpx.AsyncClient()
dummy_image = Image.new('RGB', (224, 224), (0, 0, 0))

# --- Define API Data Models (Unchanged) ---
class VideoInput(BaseModel):
    title: str
    thumbnail_url: str

class RankRequest(BaseModel):
    user_intent: str
    videos: List[VideoInput]

class RankResponse(BaseModel):
    title: str
    final_score: float
    text_score: float
    visual_score: float

# --- API Endpoint (Unchanged, but with my debug prints) ---
@app.post("/rank", response_model=List[RankResponse])
async def rank_videos_endpoint(request: RankRequest):
    if not text_model or not visual_model:
        return {"error": "Models are not loaded."}

    user_intent = request.user_intent
    
    # --- DEBUG PRINT 1 ---
    print("\n" + "="*30)
    print(f"✅ RECEIVED REQUEST FOR INTENT: '{user_intent}'")
    
    titles = [video.title for video in request.videos]
    print(f"ℹ️  Ranking {len(titles)} titles...")
    
    text_intent_vector = text_model.encode(user_intent, convert_to_tensor=True)
    text_embeddings = text_model.encode(titles, convert_to_tensor=True)
    text_scores = util.cos_sim(text_intent_vector, text_embeddings)[0]

    image_urls = [video.thumbnail_url for video in request.videos]
    pil_images = []
    
    image_requests = [client.get(url) for url in image_urls]
    responses = await asyncio.gather(*image_requests, return_exceptions=True)

    for resp in responses:
        if isinstance(resp, httpx.Response) and resp.status_code == 200:
            try:
                image_bytes = io.BytesIO(resp.content)
                pil_images.append(Image.open(image_bytes))
            except Exception:
                pil_images.append(dummy_image)
        else:
            pil_images.append(dummy_image)

    visual_intent_vector = visual_model.encode(user_intent, convert_to_tensor=True)
    visual_embeddings = visual_model.encode(pil_images, convert_to_tensor=True)
    visual_scores = util.cos_sim(visual_intent_vector, visual_embeddings)[0]
    
    results = []
    print("--- SCORES (Before Filtering) ---")
    for i in range(len(titles)):
        text_score = text_scores[i].item()
        visual_score = visual_scores[i].item()
        final_score = (TEXT_WEIGHT * text_score) + (VISUAL_WEIGHT * visual_score)
        
        print(f"  Title: {titles[i][:30]}... | Score: {final_score:.2f} (T:{text_score:.2f} V:{visual_score:.2f})")

        if final_score > MIN_SCORE:
            results.append({
                "title": titles[i],
                "final_score": final_score,
                "text_score": text_score,
                "visual_score": visual_score
            })

    ranked_results = sorted(results, key=lambda x: x['final_score'], reverse=True)
    
    print(f"✅ SENDING {len(ranked_results)} RESULTS (Filter was > {MIN_SCORE})")
    print("="*30 + "\n")
    
    return ranked_results

# --- Run the Server (Unchanged) ---
if __name__ == "__main__":
    import asyncio
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)