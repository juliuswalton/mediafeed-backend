from django.http import JsonResponse
from django.views import View
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from decouple import config


class YouTubeUserVideos(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = config('YOUTUBE_API_KEY')
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def find_channel_by_custom_url(self, custom_url, max_results=10):
        """Find a YouTube channel by its custom URL."""
        try:
            resp = self.youtube.search().list(
                q=custom_url,
                part='id',
                type='channel',
                fields='items(id(kind,channelId))',
                maxResults=max_results
            ).execute()

            channel_ids = [item['id']['channelId'] for item in resp['items'] if item['id']['kind'] == 'youtube#channel']

            if not channel_ids:
                return None

            resp = self.youtube.channels().list(
                id=','.join(channel_ids),
                part='id,snippet',
                fields='items(id,snippet(customUrl))',
                maxResults=len(channel_ids)
            ).execute()

            for item in resp['items']:
                url = item['snippet'].get('customUrl')
                if url and url.lower() == custom_url.lower():
                    return item['id']

            return None

        except HttpError as e:
            return JsonResponse({"error": f'An HTTP error {e.resp.status} occurred: {e.content}'}, status=400)

    def get(self, request, username):
        """Handle GET requests to fetch YouTube videos for a given username."""
        try:
            channel_id = self.find_channel_by_custom_url(username)
            if channel_id is None:
                return JsonResponse({"error": "No channel found for this username"}, status=404)
        except HttpError as e:
            return JsonResponse({"error": f'An HTTP error {e.resp.status} occurred: {e.content}'}, status=400)

        response = self.youtube.search().list(
            part='snippet',
            channelId=channel_id,
            maxResults=25,  # fetches 25 videos
            type='video',  # to get only videos, not playlists or channels
            order='date'  # to get the most recent videos
        ).execute()

        # Transform the data as needed
        processed_data = self.process_data(response['items'])

        return JsonResponse(processed_data, safe=False)

    def process_data(self, data):
        """Process the raw data from YouTube API to a more convenient format."""
        return [
            {
                'title': item['snippet']['title'],
                'thumbnail': item['snippet']['thumbnails']['high']['url'],  # using the high resolution thumbnail
                'link': f'https://www.youtube.com/watch?v={item["id"]["videoId"]}'
            }
            for item in data
        ]
