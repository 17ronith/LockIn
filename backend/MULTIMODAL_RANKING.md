# Step 2: Multimodal Ranking Integration

This step integrates YouTube playlist fetching with multimodal video ranking. You now have **two approaches** for ranking videos:

## Approach 1: Using Existing `videos.csv` (Legacy - Fixed Library)

**Best for**: Testing, small local datasets

```python
from video_ranker_multimodal import get_ranked_videos

user_intent = "I want to study linear algebra"
ranked_videos = get_ranked_videos(user_intent)

for video in ranked_videos[:5]:
    print(f"{video['title']}: {video['final_score']:.4f}")
```

**Pros:**
- Fast (embeddings pre-computed)
- Good for testing
- Works offline

**Cons:**
- Fixed set of videos
- Requires video_order.txt and video_image_embeddings.npy

---

## Approach 2: Using YouTube Playlists (NEW - Dynamic)

**Best for**: Production, dynamic playlists, any YouTube content

### Option A: Using `rank_youtube_playlist()` function

```python
from video_ranker_multimodal import rank_youtube_playlist
import os

api_key = os.getenv("YOUTUBE_API_KEY")
playlist_url = "https://www.youtube.com/playlist?list=PLGYFklY8P7l16uxGixgxGxWvteNuL1Psb"
user_intent = "I want to study linear algebra"

ranked_videos = rank_youtube_playlist(playlist_url, user_intent, api_key)

for video in ranked_videos[:5]:
    print(f"{video['title']}: {video['final_score']:.4f}")
    print(f"  Watch: {video['youtube_url']}")
```

### Option B: Using `PlaylistRanker` class (Recommended)

```python
from playlist_ranker import PlaylistRanker
import os

api_key = os.getenv("YOUTUBE_API_KEY")
ranker = PlaylistRanker(api_key=api_key)

playlist_url = "https://www.youtube.com/playlist?list=PLGYFklY8P7l16uxGixgxGxWvteNuL1Psb"
user_intent = "I want to study linear algebra"

# Get all ranked videos
ranked_videos = ranker.rank_playlist(playlist_url, user_intent)

# Or get filtered results (score >= 0.10)
filtered_videos = ranker.rank_playlist_filtered(playlist_url, user_intent, min_score=0.10)

for video in ranked_videos[:5]:
    print(f"{video['title']}: {video['final_score']:.4f}")
    print(f"  Text Score: {video['text_score']:.4f} | Visual Score: {video['visual_score']:.4f}")
    print(f"  Watch: {video['youtube_url']}")
```

**Pros:**
- Works with ANY YouTube playlist
- Dynamic video fetching
- No pre-processing needed
- Scales infinitely

**Cons:**
- Requires YouTube API key
- Slower (thumbnails downloaded on-demand)
- Requires internet connection

---

## Key Features

### Text Embeddings
- Generated from **video title + description**
- Title is repeated for emphasis (weighted)
- Uses fine-tuned `SentenceTransformer` model

### Visual Embeddings
- Downloaded from YouTube thumbnail URLs
- High quality: 480x360 (hqdefault)
- Max quality: 1280x720 (maxresdefault) 
- Uses CLIP-ViT-B-32 model

### Ranking Formula
```
final_score = (TEXT_WEIGHT × text_similarity) + (VISUAL_WEIGHT × visual_similarity)
             = (0.7 × text_score) + (0.3 × visual_score)
```

Weights can be adjusted in:
- `video_ranker_multimodal.py`: Lines `TEXT_WEIGHT`, `VISUAL_WEIGHT`
- `playlist_ranker.py`: Lines `TEXT_WEIGHT`, `VISUAL_WEIGHT`

---

## Output Format

Each ranked video includes:

```python
{
    'video_id': 'VIDEO_ID',
    'title': 'Video Title',
    'description': 'Video description...',
    'final_score': 0.85,           # Combined score (0.0 to 1.0)
    'text_score': 0.82,            # Text similarity
    'visual_score': 0.91,          # Visual similarity
    'thumbnail_url': 'https://...',       # Small thumbnail
    'thumbnail_url_hq': 'https://...',   # High quality (480x360)
    'thumbnail_url_max': 'https://...',  # Max quality (1280x720)
    'published_at': '2024-01-15T...',
    'youtube_url': 'https://youtube.com/watch?v=...'
}
```

---

## Performance Tips

1. **Cache Results**: Playlist metadata is cached locally in `cache/` folder
2. **Reuse RankerInstance**: Create `PlaylistRanker` once, rank multiple playlists
3. **Batch Processing**: Process multiple playlists efficiently
4. **Filter by Score**: Use `rank_playlist_filtered()` with `min_score` parameter

---

## Troubleshooting

### Error: "Module 'playlist_parser' not found"
Make sure you're in the `/backend` directory when running scripts.

### Error: "YouTube API key not set"
Set the environment variable:
```bash
export YOUTUBE_API_KEY="your_key_here"
```

### Error: "No videos found in playlist"
- Ensure the playlist URL is correct
- Playlist must be public or accessible with the API key
- Check your API quota (10,000 units per day)

### Slow thumbnail processing
- First run is slower due to downloading all thumbnails
- Subsequent runs with same intent use cache
- Consider filtering by `min_score` to reduce processing

---

## Testing

### Test with Fixed Library
```bash
cd "/Users/ronith/Documents/Projects/LockIn/backend"
python -c "from video_ranker_multimodal import get_ranked_videos; videos = get_ranked_videos('linear algebra'); print(videos[0])"
```

### Test with YouTube Playlist
```bash
cd "/Users/ronith/Documents/Projects/LockIn/backend"
python playlist_ranker.py
# Then enter: https://www.youtube.com/playlist?list=PLGYFklY8P7l16uxGixgxGxWvteNuL1Psb
# And enter intent: learn linear algebra
```

---

## Next Steps

- **Step 3**: Integrate into web application backend (FastAPI/Flask)
- **Step 4**: Build frontend to display ranked videos with YouTube player
- **Step 5**: Deploy to cloud platform
