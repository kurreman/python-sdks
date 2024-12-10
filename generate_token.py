from livekit import api
import os

token = api.AccessToken(os.getenv('LIVEKIT_API_KEY'), os.getenv('LIVEKIT_API_SECRET')) \
    .with_identity("python-bot") \
    .with_name("Python Bot") \
    .with_grants(api.VideoGrants(
        room_join=True,
        room="u3x7-mtwj",
    )).to_jwt()

print(token)