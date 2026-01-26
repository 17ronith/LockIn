# YouTube Data API Setup Guide

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on "Select a Project" → "New Project"
3. Enter a project name (e.g., "LockIn YouTube Ranker")
4. Click "Create"

## Step 2: Enable the YouTube Data API v3

1. In the Google Cloud Console, search for "YouTube Data API v3"
2. Click on "YouTube Data API v3" from the results
3. Click "Enable"

## Step 3: Create an API Key

1. Go to "Credentials" in the left sidebar
2. Click "Create Credentials" → "API Key"
3. Copy the generated API key
4. (Optional) Restrict the key to only YouTube Data API v3 for security

## Step 4: Set the Environment Variable

### macOS/Linux:
```bash
export YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY"
```

### Windows (Command Prompt):
```cmd
set YOUTUBE_API_KEY=YOUR_YOUTUBE_API_KEY
```

### Windows (PowerShell):
```powershell
$env:YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY"
```

### Permanent Setup (macOS/Linux):
Add the following line to your `~/.zshrc` or `~/.bash_profile`:
```bash
export YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY"
```
Then run: `source ~/.zshrc` or `source ~/.bash_profile`

## Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 6: Test the Integration

```bash
python playlist_parser.py
```

The script will prompt you to enter a YouTube playlist URL. It will then:
1. Fetch all videos in the playlist
2. Display the first 5 video titles
3. Attempt to fetch and display the transcript of the first video

## API Rate Limits

- **Standard Quota**: 10,000 units per day
- **Each API call costs**:
  - `playlistItems.list`: 1 unit
  - `videos.list`: 1 unit
  - `search.list`: 100 units

## Troubleshooting

### Error: "YouTube API key not set!"
- Make sure you've set the `YOUTUBE_API_KEY` environment variable
- Verify it's correctly exported

### Error: "Invalid playlist URL"
- Ensure you're using a valid YouTube playlist URL
- The URL should contain `list=` parameter
- Example: `https://www.youtube.com/playlist?list=PLxxxxxxxxxxxx`

### Error: "No transcript available"
- Not all videos have transcripts
- Only videos with captions can have transcripts
- Some creators disable transcripts on their videos

### Rate Limit Exceeded
- YouTube API has daily quota limits
- Cache is automatically used to avoid redundant API calls
- Consider clearing old cache if needed: `parser.clear_cache()`

## Features Implemented

✅ Fetch playlist videos with metadata (titles, descriptions, thumbnails)
✅ Fetch detailed video information (channel, view count, like count, etc.)
✅ Extract video transcripts (if available)
✅ Local caching to minimize API calls
✅ Batch requests for efficiency (up to 50 videos per request)
✅ Error handling and logging

## Next Steps

Once you have the `playlist_parser.py` working:
1. Integrate it with the multimodal ranking system
2. Use fetched transcripts for text embeddings
3. Download thumbnails for visual embeddings
4. Build the ranking logic in `video_ranker_multimodal.py`
