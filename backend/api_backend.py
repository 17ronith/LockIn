"""
FastAPI Backend for LockIn - Multimodal Playlist Video Ranker

This is the REST API backend that exposes the multimodal ranking system
to the frontend. It provides endpoints for:
- Ranking videos from a YouTube playlist
- Health checks
- API status

Run with:
    uvicorn api_backend:app --reload --host 0.0.0.0 --port 8000
"""

import os
import logging
import base64
import json
import hmac
import hashlib
import time
from typing import List, Optional, Dict
from datetime import datetime
from functools import lru_cache
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Header, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from supabase import create_client, Client
import uvicorn
import razorpay

from playlist_ranker import PlaylistRanker
from playlist_parser import PlaylistParser

# Load .env automatically for local development
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Initialize FastAPI App ---
app = FastAPI(
    title="LockIn API",
    description="Multimodal Video Ranking System for YouTube Playlists",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# --- CORS Configuration ---
# Allow frontend to make requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lockin-dev.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    expose_headers=["*"],
    allow_headers=["*"],
)

# --- Global State ---
PLAYLIST_RANKER: Optional[PlaylistRanker] = None
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FRONTEND_OAUTH_REDIRECT_URL = os.getenv("FRONTEND_OAUTH_REDIRECT_URL", "https://lockin-dev.vercel.app")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID") or os.getenv("razorpay_key_id")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET") or os.getenv("razorpay_key_secret")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

VIDEO_CREDIT_COST = 2
PLAYLIST_CREDIT_COST = 8
STARTER_CREDITS = 30
DEFAULT_CREDIT_PACKS = {
    "small": {"credits": 40, "amount_paise": 4900, "label": "40 credits"},
    "medium": {"credits": 100, "amount_paise": 9900, "label": "100 credits"},
    "large": {"credits": 250, "amount_paise": 19900, "label": "250 credits"}
}


def initialize_ranker():
    """Initialize the playlist ranker on startup."""
    global PLAYLIST_RANKER
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY not set. API will not function properly.")
        return False
    
    try:
        logger.info("Initializing PlaylistRanker...")
        PLAYLIST_RANKER = PlaylistRanker(api_key=YOUTUBE_API_KEY)
        logger.info("PlaylistRanker initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize PlaylistRanker: {e}")
        return False


@lru_cache(maxsize=1)
def _decode_jwt_payload(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        return None


def get_supabase_client() -> Optional[Client]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    payload = _decode_jwt_payload(SUPABASE_SERVICE_ROLE_KEY)
    if payload and payload.get("role") != "service_role":
        logger.warning("Supabase key is not a service role key. Writes may be blocked by RLS.")
    return client


def get_razorpay_client() -> razorpay.Client:
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise RuntimeError("Razorpay keys not configured")
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def get_authenticated_payload(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")
    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        return payload
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")


def get_user_credits(google_sub: str) -> Optional[int]:
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client not configured")

    result = client.table("users").select("credits").eq("google_sub", google_sub).limit(1).execute()
    if not result.data:
        return None
    return result.data[0].get("credits")


def ensure_user_credits(google_sub: str) -> int:
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client not configured")

    result = client.table("users").select("credits").eq("google_sub", google_sub).limit(1).execute()
    if not result.data:
        raise RuntimeError("User not found")

    credits = result.data[0].get("credits")
    if credits is None:
        credits = STARTER_CREDITS
        client.table("users").update({"credits": credits}).eq("google_sub", google_sub).execute()
    return credits


def add_user_credits(google_sub: str, credits_to_add: int) -> int:
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client not configured")

    result = client.table("users").select("credits").eq("google_sub", google_sub).limit(1).execute()
    if not result.data:
        raise RuntimeError("User not found")

    current = result.data[0].get("credits")
    if current is None:
        current = STARTER_CREDITS

    new_total = int(current) + int(credits_to_add)
    client.table("users").update({"credits": new_total}).eq("google_sub", google_sub).execute()
    return new_total


def upsert_user_in_supabase(payload: dict) -> dict:
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase client not configured")

    google_sub = payload.get("sub")
    if not google_sub:
        return None

    record = {
        "google_sub": google_sub,
        "email": payload.get("email"),
        "name": payload.get("name"),
        "picture": payload.get("picture")
    }

    result = client.table("users").upsert(record, on_conflict="google_sub").execute()
    if getattr(result, "error", None):
        raise RuntimeError(f"Supabase error: {result.error}")
    if result.data:
        return result.data[0]
    raise RuntimeError("Supabase upsert returned no data")


# --- Startup and Shutdown Events ---
@app.on_event("startup")
async def startup_event():
    """Run on server startup."""
    logger.info("Server starting up...")
    if os.getenv("EAGER_LOAD_RANKER", "false").lower() == "true":
        initialize_ranker()
    logger.info("Server ready to handle requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on server shutdown."""
    logger.info("Server shutting down...")


# --- Pydantic Models (Request/Response Schemas) ---

class RankingRequest(BaseModel):
    """Request model for ranking a playlist."""
    playlist_url: str = Field(
        ...,
        description="YouTube playlist URL",
        example="https://www.youtube.com/playlist?list=PLGYFklY8P7l16uxGixgxGxWvteNuL1Psb"
    )
    user_intent: str = Field(
        ...,
        description="Natural language description of what user wants to learn",
        example="I want to learn linear algebra"
    )
    min_score: float = Field(
        default=0.0,
        description="Minimum relevance score (0.0 to 1.0) to include in results",
        ge=0.0,
        le=1.0
    )
    limit: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=100
    )
    
    @validator('playlist_url')
    def validate_playlist_url(cls, v):
        """Validate that the URL is a YouTube playlist URL."""
        if not v or "list=" not in v:
            raise ValueError("Invalid YouTube playlist URL (missing list=)")
        return v
    
    @validator('user_intent')
    def validate_user_intent(cls, v):
        """Validate that user intent is not empty."""
        if not v or len(v.strip()) == 0:
            raise ValueError("User intent cannot be empty")
        return v.strip()


class VideoRequest(BaseModel):
    """Request model for single video lookup."""
    video_url: str = Field(
        ...,
        description="YouTube video URL or ID",
        example="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )

    @validator('video_url')
    def validate_video_url(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Video URL cannot be empty")
        return v.strip()


class VideoResult(BaseModel):
    """Response model for a single video result."""
    rank: int
    video_id: str
    title: str
    description: str
    final_score: float
    text_score: float
    visual_score: float
    thumbnail_url: str
    thumbnail_url_hq: str
    thumbnail_url_max: Optional[str]
    youtube_url: str
    published_at: Optional[str]


class RankingResponse(BaseModel):
    """Response model for ranking results."""
    status: str = Field(default="success", description="Response status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    playlist_url: str = Field(description="URL of the ranked playlist")
    user_intent: str = Field(description="User's search intent")
    total_videos: int = Field(description="Total videos in playlist")
    returned_results: int = Field(description="Number of results returned after filtering")
    videos: List[VideoResult] = Field(description="List of ranked videos")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: datetime
    ranker_ready: bool
    api_key_configured: bool
    version: str


class ErrorResponse(BaseModel):
    """Response model for errors."""
    status: str = "error"
    timestamp: datetime = Field(default_factory=datetime.now)
    message: str
    detail: Optional[str] = None


class AuthRequest(BaseModel):
    """Request model for Google OAuth login."""
    credential: str = Field(..., description="Google ID token credential")


class UserProfile(BaseModel):
    """User profile returned after authentication."""
    id: str
    email: str
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None


class AuthResponse(BaseModel):
    """Response model for authentication."""
    status: str = "success"
    user: UserProfile
    token: str


class BillingPack(BaseModel):
    pack_id: str
    credits: int
    amount_paise: int
    currency: str = "INR"
    label: str


class BillingConfigResponse(BaseModel):
    key_id: str
    currency: str
    packs: List[BillingPack]
    video_credit_cost: int
    playlist_credit_cost: int


class CreateOrderRequest(BaseModel):
    pack_id: str


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    pack: BillingPack


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class CreditsResponse(BaseModel):
    credits: int


def get_credit_pack(pack_id: str) -> BillingPack:
    pack = DEFAULT_CREDIT_PACKS.get(pack_id)
    if not pack:
        raise HTTPException(status_code=400, detail="Invalid credit pack")
    return BillingPack(
        pack_id=pack_id,
        credits=pack["credits"],
        amount_paise=pack["amount_paise"],
        currency="INR",
        label=pack["label"]
    )


def list_credit_packs() -> List[BillingPack]:
    return [get_credit_pack(pack_id) for pack_id in DEFAULT_CREDIT_PACKS]


class SessionCompleteRequest(BaseModel):
    """Request model for completed focus session."""
    focus_minutes: int = Field(..., ge=1)
    break_minutes: int = Field(..., ge=1)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@app.get("/auth/google", tags=["Auth"])
async def auth_google_redirect():
    """Start Google OAuth via redirect-based flow."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_OAUTH_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_OAUTH_REDIRECT_URI."
        )

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=url, status_code=302)


@app.get("/auth/google/callback", tags=["Auth"])
async def auth_google_callback(code: Optional[str] = None, error: Optional[str] = None):
    """Handle Google OAuth redirect and exchange code for tokens."""
    if error:
        return RedirectResponse(url=f"{FRONTEND_OAUTH_REDIRECT_URL}/login?error={error}", status_code=302)

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_OAUTH_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_OAUTH_REDIRECT_URI."
        )

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if token_response.status_code != 200:
        logger.error("Google token exchange failed: %s", token_response.text)
        raise HTTPException(status_code=401, detail="Token exchange failed")

    token_json = token_response.json()
    id_token_value = token_json.get("id_token")
    if not id_token_value:
        raise HTTPException(status_code=401, detail="Missing id_token")

    try:
        payload = id_token.verify_oauth2_token(
            id_token_value,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    try:
        upsert_user_in_supabase(payload)
    except Exception:
        logger.exception("Failed to upsert user in Supabase (non-fatal, continuing login)")

    redirect_url = f"{FRONTEND_OAUTH_REDIRECT_URL}/login?token={id_token_value}"
    return RedirectResponse(url=redirect_url, status_code=302)


@app.post("/auth/google", response_model=AuthResponse, tags=["Auth"])
async def auth_google(request: AuthRequest):
    """Verify Google ID token and return user profile."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID."
        )

    try:
        payload = id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    try:
        upsert_user_in_supabase(payload)
    except Exception as exc:
        logger.exception("Failed to upsert user in Supabase (non-fatal, continuing login)")

    user = UserProfile(
        id=payload.get("sub", ""),
        email=payload.get("email", ""),
        name=payload.get("name", ""),
        given_name=payload.get("given_name"),
        family_name=payload.get("family_name"),
        picture=payload.get("picture")
    )

    return AuthResponse(user=user, token=request.credential)


@app.get("/me", response_model=UserProfile, tags=["Auth"])
async def get_me(authorization: Optional[str] = Header(None)):
    """Return the current user from the Google token and sync to Supabase."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        upsert_user_in_supabase(payload)
    except Exception as exc:
        logger.exception("Failed to upsert user in Supabase")
        raise HTTPException(status_code=500, detail="Failed to sync user")

    return UserProfile(
        id=payload.get("sub", ""),
        email=payload.get("email", ""),
        name=payload.get("name", ""),
        given_name=payload.get("given_name"),
        family_name=payload.get("family_name"),
        picture=payload.get("picture")
    )


@app.get("/billing/config", response_model=BillingConfigResponse, tags=["Billing"])
async def get_billing_config():
    if not RAZORPAY_KEY_ID:
        raise HTTPException(status_code=500, detail="Razorpay key not configured")

    return BillingConfigResponse(
        key_id=RAZORPAY_KEY_ID,
        currency="INR",
        packs=list_credit_packs(),
        video_credit_cost=VIDEO_CREDIT_COST,
        playlist_credit_cost=PLAYLIST_CREDIT_COST
    )


@app.get("/billing/credits", response_model=CreditsResponse, tags=["Billing"])
async def get_credits(authorization: Optional[str] = Header(None)):
    payload = get_authenticated_payload(authorization)
    google_sub = payload.get("sub")
    if not google_sub:
        raise HTTPException(status_code=401, detail="Invalid user")

    try:
        credits = ensure_user_credits(google_sub)
    except Exception as exc:
        logger.exception("Failed to load credits")
        raise HTTPException(status_code=500, detail="Unable to load credits")

    return CreditsResponse(credits=credits)


@app.post("/billing/create-order", response_model=CreateOrderResponse, tags=["Billing"])
async def create_order(request: CreateOrderRequest, authorization: Optional[str] = Header(None)):
    payload = get_authenticated_payload(authorization)
    google_sub = payload.get("sub")
    if not google_sub:
        raise HTTPException(status_code=401, detail="Invalid user")

    pack = get_credit_pack(request.pack_id)
    client = get_razorpay_client()

    try:
        order = client.order.create({
            "amount": pack.amount_paise,
            "currency": pack.currency,
            "receipt": f"lockin_{google_sub}_{int(time.time())}",
            "notes": {
                "user_id": google_sub,
                "pack_id": pack.pack_id
            }
        })
    except Exception as exc:
        logger.exception("Failed to create Razorpay order")
        raise HTTPException(status_code=500, detail="Unable to create order")

    return CreateOrderResponse(
        order_id=order.get("id"),
        amount=order.get("amount"),
        currency=order.get("currency"),
        key_id=RAZORPAY_KEY_ID,
        pack=pack
    )


@app.post("/billing/verify-payment", response_model=CreditsResponse, tags=["Billing"])
async def verify_payment(request: VerifyPaymentRequest, authorization: Optional[str] = Header(None)):
    payload = get_authenticated_payload(authorization)
    google_sub = payload.get("sub")
    if not google_sub:
        raise HTTPException(status_code=401, detail="Invalid user")

    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": request.razorpay_order_id,
            "razorpay_payment_id": request.razorpay_payment_id,
            "razorpay_signature": request.razorpay_signature
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    order = client.order.fetch(request.razorpay_order_id)
    notes = order.get("notes", {}) or {}
    if notes.get("user_id") != google_sub:
        raise HTTPException(status_code=403, detail="Order does not belong to user")

    pack_id = notes.get("pack_id")
    pack = get_credit_pack(pack_id)
    if order.get("amount") != pack.amount_paise:
        raise HTTPException(status_code=400, detail="Order amount mismatch")

    try:
        new_total = add_user_credits(google_sub, pack.credits)
    except Exception:
        logger.exception("Failed to add credits")
        raise HTTPException(status_code=500, detail="Failed to add credits")

    return CreditsResponse(credits=new_total)


@app.post("/billing/webhook", tags=["Billing"])
async def razorpay_webhook(request: Request):
    if not RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    signature = request.headers.get("X-Razorpay-Signature") or request.headers.get("x-razorpay-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature")

    body = await request.body()
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = json.loads(body.decode("utf-8"))
    event = payload.get("event")

    if event in {"payment.captured", "order.paid"}:
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        notes = payment_entity.get("notes") or order_entity.get("notes") or {}
        google_sub = notes.get("user_id")
        pack_id = notes.get("pack_id")

        if google_sub and pack_id:
            try:
                pack = get_credit_pack(pack_id)
                add_user_credits(google_sub, pack.credits)
            except Exception:
                logger.exception("Failed to add credits from webhook")
                raise HTTPException(status_code=500, detail="Failed to process webhook")

    return {"status": "ok"}


@app.post("/sessions/complete", tags=["Sessions"])
async def complete_session(
    request: SessionCompleteRequest,
    authorization: Optional[str] = Header(None)
):
    """Store a completed focus session for the authenticated user."""
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_record = upsert_user_in_supabase(payload)
    except Exception:
        logger.exception("Failed to upsert user in Supabase")
        raise HTTPException(status_code=500, detail="Unable to resolve user")

    record = {
        "user_id": user_record.get("id"),
        "focus_minutes": request.focus_minutes,
        "break_minutes": request.break_minutes,
        "started_at": request.started_at,
        "completed_at": request.completed_at or datetime.now()
    }

    client.table("sessions").insert(record).execute()
    return {"status": "success"}


@app.post("/video", response_model=VideoResult, tags=["Video"])
async def get_video(request: VideoRequest):
    """Fetch metadata for a single YouTube video."""
    if not YOUTUBE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="API not ready. YouTube API key may not be configured."
        )

    try:
        parser = PlaylistParser(api_key=YOUTUBE_API_KEY)
        video_id = parser._get_video_id_from_url(request.video_url)
        details = parser.fetch_video_details(video_id, use_cache=True)

        if not details:
            raise HTTPException(
                status_code=400,
                detail="Please make sure the YouTube video is public and available."
            )

        thumbnail_url_hq = parser.get_thumbnail_url(video_id, quality="hqdefault")
        thumbnail_url_max = parser.get_thumbnail_url(video_id, quality="maxresdefault")

        return VideoResult(
            rank=1,
            video_id=video_id,
            title=details.get("title", ""),
            description=details.get("description", ""),
            final_score=1.0,
            text_score=1.0,
            visual_score=1.0,
            thumbnail_url=details.get("thumbnail_url", thumbnail_url_hq),
            thumbnail_url_hq=thumbnail_url_hq,
            thumbnail_url_max=thumbnail_url_max,
            youtube_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=details.get("published_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during video lookup")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# --- API Endpoints ---

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - provides API information."""
    return {
        "name": "LockIn API",
        "version": "1.0.0",
        "description": "Multimodal Video Ranking System for YouTube Playlists",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse: Current status of the API and its dependencies
    """
    return HealthResponse(
        status="healthy" if PLAYLIST_RANKER else "degraded",
        timestamp=datetime.now(),
        ranker_ready=PLAYLIST_RANKER is not None,
        api_key_configured=bool(YOUTUBE_API_KEY),
        version="1.0.0"
    )


@app.post("/rank", response_model=RankingResponse, tags=["Ranking"])
async def rank_playlist(request: RankingRequest, background_tasks: BackgroundTasks):
    """
    Rank videos from a YouTube playlist based on user intent.
    
    This endpoint:
    1. Fetches all videos from the YouTube playlist
    2. Generates text embeddings from titles/descriptions
    3. Generates visual embeddings from thumbnails
    4. Ranks videos using weighted combination
    5. Returns top results sorted by relevance
    
    Args:
        request: RankingRequest with playlist URL and user intent
        
    Returns:
        RankingResponse: Ranked videos with scores and metadata
        
    Raises:
        HTTPException: If playlist is invalid or ranking fails
    """
    
    # Validate API is ready
    if not PLAYLIST_RANKER:
        if not initialize_ranker():
            logger.error("PlaylistRanker not initialized")
            raise HTTPException(
                status_code=503,
                detail="API not ready. YouTube API key may not be configured."
            )
    
    try:
        logger.info(f"Ranking request: playlist={request.playlist_url[:50]}..., intent={request.user_intent}")
        
        # Rank the playlist
        ranked_videos = PLAYLIST_RANKER.rank_playlist(
            request.playlist_url,
            request.user_intent
        )
        
        if not ranked_videos:
            raise HTTPException(
                status_code=400,
                detail="Please make your YouTube playlist public to continue"
            )
        
        # Filter by minimum score
        filtered_videos = [
            v for v in ranked_videos if v['final_score'] >= request.min_score
        ]
        
        # Limit results
        limited_videos = filtered_videos[:request.limit]
        
        # Add rank field
        for rank, video in enumerate(limited_videos, 1):
            video['rank'] = rank
        
        # Create response
        response = RankingResponse(
            status="success",
            timestamp=datetime.now(),
            playlist_url=request.playlist_url,
            user_intent=request.user_intent,
            total_videos=len(ranked_videos),
            returned_results=len(limited_videos),
            videos=[VideoResult(**v) for v in limited_videos]
        )
        
        logger.info(f"Successfully ranked {len(limited_videos)} videos from {len(ranked_videos)} total")
        
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during ranking: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/rank-fixed", response_model=RankingResponse, tags=["Ranking"])
async def rank_fixed_library(
    user_intent: str = Query(..., description="What would you like to focus on?"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum relevance score")
):
    """
    Rank videos from the fixed library (videos.csv).
    
    This endpoint ranks against the pre-loaded video library instead of
    fetching from YouTube. Useful for testing and demo purposes.
    
    Args:
        user_intent: Natural language query
        limit: Maximum results to return
        min_score: Minimum relevance score
        
    Returns:
        RankingResponse: Ranked videos
    """
    try:
        from video_ranker_multimodal import get_ranked_videos
        
        logger.info(f"Fixed library ranking: intent={user_intent}")
        
        ranked_videos = get_ranked_videos(user_intent)
        
        if not ranked_videos:
            raise HTTPException(
                status_code=500,
                detail="Could not load fixed video library"
            )
        
        # Filter and limit
        filtered = [v for v in ranked_videos if v.get('final_score', 0) >= min_score]
        limited = filtered[:limit]
        
        # Transform to proper format
        transformed_videos = []
        for rank, video in enumerate(limited, 1):
            thumb_path = video.get('thumbnail_path', '')
            transformed = {
                'rank': rank,
                'video_id': video.get('title', '').replace(' ', '_')[:20],
                'title': video.get('title', ''),
                'description': video.get('transcript', ''),  # Use transcript as description
                'final_score': video.get('final_score', 0),
                'text_score': video.get('text_score', 0),
                'visual_score': video.get('visual_score', 0),
                'thumbnail_url': thumb_path,
                'thumbnail_url_hq': thumb_path,
                'thumbnail_url_max': thumb_path,
                'youtube_url': "#",  # Placeholder
                'published_at': None
            }
            transformed_videos.append(transformed)
        
        response = RankingResponse(
            status="success",
            playlist_url="fixed://library",
            user_intent=user_intent,
            total_videos=len(ranked_videos),
            returned_results=len(limited),
            videos=[VideoResult(**v) for v in transformed_videos]
        )
        
        logger.info(f"Fixed library: returned {len(limited)} videos")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in fixed library ranking: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error ranking fixed library: {str(e)}"
        )


@app.get("/info", tags=["Info"])
async def api_info():
    """Get API information and configuration."""
    return {
        "name": "LockIn Multimodal Ranking API",
        "version": "1.0.0",
        "endpoints": {
            "GET /": "Root endpoint",
            "GET /health": "Health check",
            "POST /rank": "Rank YouTube playlist videos",
            "GET /rank-fixed": "Rank fixed library videos",
            "GET /docs": "Swagger UI documentation",
            "GET /redoc": "ReDoc documentation",
            "GET /info": "API information"
        },
        "models": {
            "text": "./my-finetuned-model",
            "visual": "clip-ViT-B-32"
        },
        "weights": {
            "text_weight": 0.7,
            "visual_weight": 0.3
        }
    }


# --- Error Handlers ---

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions."""
    logger.error(f"ValueError: {exc}")
    return {
        "status": "error",
        "message": str(exc),
        "timestamp": datetime.now()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return {
        "status": "error",
        "message": "An unexpected error occurred",
        "timestamp": datetime.now()
    }


# --- Development Entry Point ---

if __name__ == "__main__":
    # Check if API key is set
    if not YOUTUBE_API_KEY:
        print("WARNING: YOUTUBE_API_KEY environment variable not set!")
        print("The /rank endpoint will not work without it.")
        print("Set it with: export YOUTUBE_API_KEY='your_key_here'")
    
    # Run the server
    uvicorn.run(
        "api_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
