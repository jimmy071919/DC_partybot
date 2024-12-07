from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY

def search_youtube(query):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=10
    )
    response = request.execute()
    
    videos = []
    for item in response['items']:
        video = {
            "title": item['snippet']['title'],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            "channel": item['snippet']['channelTitle']
        }
        videos.append(video)
    return videos
