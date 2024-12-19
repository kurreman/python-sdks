from livekit import api
import os

token = api.AccessToken(os.getenv('LIVEKIT_API_KEY'), os.getenv('LIVEKIT_API_SECRET')) \
    .with_identity("python-bot") \
    .with_name("Python Bot") \
    .with_grants(api.VideoGrants(
        room_join=True,
        room=os.getenv('LIVEKIT_ROOM_NAME'),
    )).to_jwt()

print(token)