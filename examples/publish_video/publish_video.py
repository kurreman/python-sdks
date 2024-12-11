import asyncio
import colorsys
import logging
import os
from signal import SIGINT, SIGTERM

import numpy as np
from livekit import api, rtc
import cv2

WIDTH, HEIGHT = 3840, 2160


# ensure LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET are set


async def main(room: rtc.Room):
    # token = (
    #     api.AccessToken()
    #     .with_identity("python-publisher")
    #     .with_name("Python Publisher")
    #     .with_grants(
    #         api.VideoGrants(
    #             room_join=True,
    #             room="my-room",
    #         )
    #     )
    #     .to_jwt()
    # )
    token = os.getenv("LIVEKIT_TOKEN")
    url = os.getenv("LIVEKIT_URL")
    logging.info("connecting to %s", url)
    try:
        await room.connect(url, token)
        logging.info("connected to room %s", room.name)
    except rtc.ConnectError as e:
        logging.error("failed to connect to the room: %s", e)
        return

    # publish a track
    source = rtc.VideoSource(WIDTH, HEIGHT)
    track = rtc.LocalVideoTrack.create_video_track("hue", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_CAMERA
    publication = await room.local_participant.publish_track(track, options)
    logging.info("published track %s", publication.sid)

    asyncio.ensure_future(draw_color_cycle(source))


async def draw_color_cycle(source: rtc.VideoSource):
    # argb_frame = bytearray(WIDTH * HEIGHT * 4)
    # arr = np.frombuffer(argb_frame, dtype=np.uint8)

    path = "examples/publish_video/casper_koray_vallentuna.MP4"
    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        print("Error opening video file")
        return

    # framerate = 1 / 30
    # hue = 0.0

    framerate = cap.get(cv2.CAP_PROP_FPS)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        start_time = asyncio.get_event_loop().time()

        # rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        # rgb = [(x * 255) for x in rgb]  # type: ignore

        # argb_color = np.array(rgb + [255], dtype=np.uint8)
        # arr.flat[::4] = argb_color[0]
        # arr.flat[1::4] = argb_color[1]
        # arr.flat[2::4] = argb_color[2]
        # arr.flat[3::4] = argb_color[3]

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        argb_frame = frame.tobytes()
        assert isinstance(argb_frame, (bytearray, bytes)) and len(argb_frame) == WIDTH * HEIGHT * 4, (
            f"argb_frame should be a bytearray of length WIDTH*HEIGHT*4={WIDTH*HEIGHT*4} but it is {type(argb_frame)} of length {len(argb_frame)}"
        )

        frame = rtc.VideoFrame(WIDTH, 
                               HEIGHT, 
                               rtc.VideoBufferType.RGBA, 
                               argb_frame)
        
        source.capture_frame(frame)
        # hue = (hue + framerate / 3) % 1.0

        code_duration = asyncio.get_event_loop().time() - start_time
        await asyncio.sleep(1 / framerate - code_duration)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logging.FileHandler("publish_hue.log"), logging.StreamHandler()],
    )

    loop = asyncio.get_event_loop()
    room = rtc.Room(loop=loop)

    async def cleanup():
        await room.disconnect()
        loop.stop()

    asyncio.ensure_future(main(room))
    for signal in [SIGINT, SIGTERM]:
        loop.add_signal_handler(signal, lambda: asyncio.ensure_future(cleanup()))

    try:
        loop.run_forever()
    finally:
        loop.close()
