import asyncio
import cv2
import os
import time
from datetime import datetime
import numpy as np
from livekit import api, rtc

# Ensure LIVEKIT_URL and LIVEKIT_TOKEN are set as environment variables
WIDTH = 1920
HEIGHT = 1080

async def stream_video_to_livekit(video_path, room: rtc.Room):
    token = os.getenv("LIVEKIT_TOKEN")
    url = os.getenv("LIVEKIT_URL")

    try:
        await room.connect(url, token)
        print(f"Connected to room: {room.name}")
    except rtc.ConnectError as e:
        print(f"Failed to connect to the room: {e}")
        return

    # Create video source and track
    video_source = rtc.VideoSource(WIDTH, HEIGHT)
    video_track = rtc.LocalVideoTrack.create_video_track("video", video_source)
    await room.local_participant.publish_track(video_track)
    print("Video track published.")

    # Stream video frames
    await stream_video_frames(video_path, video_source)

async def stream_video_frames(video_path, video_source: rtc.VideoSource):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error opening video file")
        return

    framerate = cap.get(cv2.CAP_PROP_FPS)
    delay = 1 / framerate

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Add timestamp to the frame
        timestamp = int(time.time() * 1000)  # Milliseconds since epoch
        timestamp_text = f"{timestamp}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        font_thickness = 2
        text_size, _ = cv2.getTextSize(timestamp_text, font, font_scale, font_thickness)
        text_x = 10
        text_y = text_size[1] + 10
        cv2.rectangle(frame, (text_x - 5, text_y - text_size[1] - 5), 
                      (text_x + text_size[0] + 5, text_y + 5), (255, 255, 255), -1)
        cv2.putText(frame, timestamp_text, (text_x, text_y), font, font_scale, (0, 0, 255), font_thickness)

        # Display frame locally
        # cv2.imshow("Local Video", frame)
        if cv2.waitKey(int(delay * 1000)) & 0xFF == ord('q'):
            break

        # Prepare frame for LiveKit
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        argb_frame = frame.tobytes()
        video_frame = rtc.VideoFrame(
            WIDTH,
            HEIGHT,
            rtc.VideoBufferType.RGBA,
            argb_frame,
        )
        video_source.capture_frame(video_frame)

        await asyncio.sleep(delay)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    room = rtc.Room(loop=loop)

    video_file_path = "examples/publish_video/casper_koray_vallentuna_lowres.MP4"

    async def cleanup():
        await room.disconnect()
        loop.stop()

    try:
        asyncio.ensure_future(stream_video_to_livekit(video_file_path, room))
        loop.run_forever()
    except KeyboardInterrupt:
        asyncio.run(cleanup())
    finally:
        loop.close()
