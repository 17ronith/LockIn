 LockIn API Backend Documentation

## Overview

The FastAPI backend exposes the multimodal ranking system through REST endpoints. It handles:
- YouTube playlist ranking requests
- Fixed library ranking (for testing)
- Health checks and API status
- Request validation and error handling

---

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt 
```

### 2. Set Environment Variable

```bash
export YOUTUBE_API_KEY="your_api_key_here"
```

### 3. Start the Server

```bash
# Development mode (with auto-reload)
uvicorn api_backend:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn api_backend:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Root Info**: http://localhost:8000

---

## API Endpoints

### Health Check

#### GET `/health`

Check if the API is ready and YouTube API is configured.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-23T15:30:00",
  "ranker_ready": true,
  "api_key_configured": true,
  "version": "1.0.0"
}
```

---

### Rank YouTube Playlist

#### POST `/rank`

Rank videos from a YouTube playlist based on user intent.

**Request Body:**
```json
{
  "playlist_url": "https://www.youtube.com/playlist?list=PLGYFklY8P7l16uxGixgxGxWvteNuL1Psb",
  "user_intent": "I want to learn linear algebra",
  "min_score": 0.1,
  "limit": 10
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `playlist_url` | string | Yes | YouTube playlist URL with `list=` parameter |
| `user_intent` | string | Yes | What the user wants to learn (natural language) |
| `min_score` | float | No | Filter results with score >= this value (0.0-1.0). Default: 0.0 |
| `limit` | integer | No | Maximum results to return (1-100). Default: 10 |

**Response (200 OK):**
```json
{
  "status": "success",
  "timestamp": "2024-01-23T15:30:00",
  "playlist_url": "https://www.youtube.com/playlist?list=PLGYFklY8P7l16uxGixgxGxWvteNuL1Psb",
  "user_intent": "I want to learn linear algebra",
  "total_videos": 20,
  "returned_results": 5,
  "videos": [
    {
      "rank": 1,
      "video_id": "dQw4w9WgXcQ",
      "title": "Linear Algebra Full Course - MIT 18.06",
      "description": "Learn matrix multiplication, eigenvalues, eigenvectors...",
      "final_score": 0.8523,
      "text_score": 0.8921,
      "visual_score": 0.7234,
      "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
      "thumbnail_url_hq": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
      "thumbnail_url_max": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
      "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "published_at": "2023-01-15T10:30:00Z"
    },
    ...
  ]
}
```

**Error Responses:**
- `400 Bad Request`: Invalid playlist URL or empty user intent
- `503 Service Unavailable`: API not ready (YouTube API key not configured)
- `500 Internal Server Error`: Unexpected error during ranking

---

### Rank Fixed Library

#### GET `/rank-fixed`

Rank videos from the pre-loaded fixed library (for testing without YouTube API).

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_intent` | string | Required | What to search for |
| `limit` | integer | 10 | Max results (1-100) |
| `min_score` | float | 0.0 | Minimum score filter |

**Example Request:**
```
GET /rank-fixed?user_intent=linear+algebra&limit=5&min_score=0.1
```

**Response Format:** Same as `/rank` endpoint

---

### API Info

#### GET `/info`

Get API configuration and available endpoints.

**Response:**
```json
{
  "name": "LockIn Multimodal Ranking API",
  "version": "1.0.0",
  "endpoints": {
    "GET /": "Root endpoint",
    "GET /health": "Health check",
    "POST /rank": "Rank YouTube playlist videos",
    "GET /rank-fixed": "Rank fixed library videos",
    "GET /docs": "Swagger UI",
    "GET /redoc": "ReDoc",
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
```

---

## Usage Examples

### Python (requests library)

```python
import requests

API_URL = "http://localhost:8000"

# Rank a playlist
response = requests.post(
    f"{API_URL}/rank",
    json={
        "playlist_url": "https://www.youtube.com/playlist?list=PLGYFklY8P7l16uxGixgxGxWvteNuL1Psb",
        "user_intent": "I want to learn linear algebra",
        "min_score": 0.2,
        "limit": 5
    }
)

results = response.json()
for video in results["videos"]:
    print(f"{video['rank']}. {video['title']} ({video['final_score']:.4f})")
    print(f"   Watch: {video['youtube_url']}")
```

### JavaScript (fetch API)

```javascript
const API_URL = "http://localhost:8000";

async function rankPlaylist(playlistUrl, userIntent) {
  const response = await fetch(`${API_URL}/rank`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      playlist_url: playlistUrl,
      user_intent: userIntent,
      min_score: 0.2,
      limit: 10
    })
  });

  const results = await response.json();
  
  results.videos.forEach(video => {
    console.log(`${video.rank}. ${video.title}`);
    console.log(`Score: ${video.final_score.toFixed(4)}`);
    console.log(`Watch: ${video.youtube_url}`);
  });
}

rankPlaylist(
  "https://www.youtube.com/playlist?list=PLGYFklY8P7l16uxGixgxGxWvteNuL1Psb",
  "hip hop music"
);
```

### cURL

```bash
curl -X POST http://localhost:8000/rank \
  -H "Content-Type: application/json" \
  -d '{
    "playlist_url": "https://www.youtube.com/playlist?list=PLGYFklY8P7l16uxGixgxGxWvteNuL1Psb",
    "user_intent": "I want to learn linear algebra",
    "min_score": 0.2,
    "limit": 5
  }'
```

---

## CORS Configuration

The API is configured to accept requests from any origin (in development). For production:

```python
# In api_backend.py, update CORSMiddleware:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specify your frontend URL
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "timestamp": "2024-01-23T15:30:00",
  "detail": "Optional additional detail"
}
```

### Common Errors:

#### Invalid Playlist URL
```
Status: 400
{
  "status": "error",
  "message": "Invalid YouTube playlist URL",
  "detail": "URL must contain 'youtube.com' and 'list=' parameter"
}
```

#### API Not Ready
```
Status: 503
{
  "status": "error",
  "message": "API not ready. YouTube API key may not be configured.",
  "detail": "Set YOUTUBE_API_KEY environment variable"
}
```

#### No Videos Found
```
Status: 400
{
  "status": "error",
  "message": "No videos found in playlist",
  "detail": "Playlist may be private or URL may be invalid"
}
```

---

## Performance Considerations

### Request Timing
- First request for a playlist: **30-60 seconds** (downloads thumbnails)
- Subsequent requests: **5-10 seconds** (cached)

### Caching Strategy
- Playlist metadata cached in `cache/` folder
- Thumbnails downloaded on-demand from YouTube CDN
- Cache persists between server restarts

### Optimization Tips
1. **Reuse connections** - Keep API connection alive
2. **Use min_score filter** - Only retrieve relevant videos
3. **Batch requests** - Process multiple playlists efficiently
4. **Cache aware** - Second request for same playlist is faster

---

## Deployment

### Docker
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV YOUTUBE_API_KEY=${YOUTUBE_API_KEY}

CMD ["uvicorn", "api_backend:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Heroku
```bash
heroku create your-app-name
heroku config:set YOUTUBE_API_KEY=your_key_here
git push heroku main
```

### AWS/Azure
- Use managed container services (ECS, ACI)
- Set environment variables in deployment config
- Use load balancers for multiple instances

---

## Monitoring & Logging

The API logs all requests and errors. To view logs:

```bash
# Development server logs
# Check console output

# Production with file logging
# Implement logging handler in api_backend.py
```

---

## Next Steps

1. Build the React/Vue frontend to consume these endpoints
2. Integrate YouTube IFrame Player API for video playback
3. Deploy to production (Heroku, AWS, etc.)
4. Add authentication if needed
5. Scale based on traffic

See `Step 4: Web Application Frontend` for frontend integration.
