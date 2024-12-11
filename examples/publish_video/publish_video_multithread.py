import asyncio
import colorsys
import logging
import os
from signal import SIGINT, SIGTERM
from queue import Queue
from threading import Thread

import numpy as np
from livekit import api, rtc
import cv2

from datetime import datetime

import time
from collections import deque

# WIDTH, HEIGHT = 3840, 2160
WIDTH, HEIGHT = 1920, 1080


# Thread-safe queue for frame sharing
argb_frame_queue = deque(maxlen=3)

FRAMERATE = None

def frame_capturer(video_path, queue):
    global FRAMERATE
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error opening video file",flush=True)
        return

    FRAMERATE = cap.get(cv2.CAP_PROP_FPS)
    print(f"FRAMERATE: {FRAMERATE}",flush=True)
    print(f"max queue size in seconds: {queue.maxlen/FRAMERATE}",flush=True)
    while cap.isOpened():
        start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = int(time.time() * 1000)
        print(f"frame timestamp: {timestamp}",flush=True)
        timestamp_text = f"{timestamp}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 5
        font_thickness = 2

        text_size, _ = cv2.getTextSize(timestamp_text, font, font_scale, font_thickness)
        text_x = 10
        text_y = text_size[1] + 10

        cv2.rectangle(frame, (text_x - 5, text_y - text_size[1] - 5), (text_x + text_size[0] + 5, text_y + 5), (255, 255, 255), -1)
        cv2.putText(frame, timestamp_text, (text_x, text_y), font, font_scale, (0, 0, 255), font_thickness)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        argb_frame = frame.tobytes()
        assert isinstance(argb_frame, (bytearray, bytes)) and len(argb_frame) == WIDTH * HEIGHT * 4, (
                f"argb_frame should be a bytearray of length WIDTH*HEIGHT*4={WIDTH*HEIGHT*4} but it is {type(argb_frame)} of length {len(argb_frame)}"
            )
        
        # if len(queue) == queue.maxlen:
        #     print("queue is full, removing oldest frame")
        #     # queue.popleft()  # Remove the oldest frame if the deque is full
        queue.append(argb_frame)  # Add the newest frame
        code_duration = time.time() - start_time
        # print(f"code_duration: {code_duration}")
        if code_duration > 1 / FRAMERATE:
            pass
        else:
            time.sleep(1 / FRAMERATE - code_duration)
        print(f"frame_capture_loop_fps: {1 / (time.time()- start_time)}",flush=True)

    cap.release()

def start_frame_capture_thread(video_path):
    thread = Thread(target=frame_capturer, args=(video_path, argb_frame_queue), daemon=True)
    thread.start()
    return thread

async def main(room: rtc.Room):
    token = os.getenv("LIVEKIT_TOKEN")
    url = os.getenv("LIVEKIT_URL")
    logging.info("connecting to %s", url)
    try:
        await room.connect(url, token)
        logging.info("connected to room %s", room.name)
    except rtc.ConnectError as e:
        logging.error("failed to connect to the room: %s", e)
        return

    # Publish a track
    source = rtc.VideoSource(WIDTH, HEIGHT)
    track = rtc.LocalVideoTrack.create_video_track("hue", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_CAMERA
    publication = await room.local_participant.publish_track(track, options)
    logging.info("published track %s", publication.sid)

    asyncio.ensure_future(draw_color_cycle(source))

async def draw_color_cycle(source: rtc.VideoSource):
    global FRAMERATE
    while True:
        if FRAMERATE:
            if len(argb_frame_queue) > 0:
                # frame = frame_queue.get()
                # argb_frame = frame.tobytes()
                # assert isinstance(argb_frame, (bytearray, bytes)) and len(argb_frame) == WIDTH * HEIGHT * 4, (
                #     f"argb_frame should be a bytearray of length WIDTH*HEIGHT*4={WIDTH*HEIGHT*4} but it is {type(argb_frame)} of length {len(argb_frame)}"
                # )
                start_time = asyncio.get_event_loop().time()

                # argb_frame = argb_frame_queue.get()
                argb_frame = argb_frame_queue.pop()

                video_frame = rtc.VideoFrame(
                    WIDTH,
                    HEIGHT,
                    rtc.VideoBufferType.RGBA,
                    argb_frame,
                )

                source.capture_frame(video_frame)

            code_duration = asyncio.get_event_loop().time() - start_time
            await asyncio.sleep(1 / FRAMERATE - code_duration)
            print(f"frame_stream_loop_fps: {1 / (asyncio.get_event_loop().time()- start_time)}",flush=True)

if __name__ == "__main__":
    # logging.basicConfig(
    #     level=logging.INFO,
    #     handlers=[logging.FileHandler("publish_hue.log"), logging.StreamHandler()],
    # )

    loop = asyncio.get_event_loop()
    room = rtc.Room(loop=loop)

    async def cleanup():
        await room.disconnect()
        loop.stop()

    # video_path = "examples/publish_video/casper_koray_vallentuna.MP4"
    video_path = "examples/publish_video/casper_koray_vallentuna_lowres.MP4"
    start_frame_capture_thread(video_path)

    asyncio.ensure_future(main(room))
    for signal in [SIGINT, SIGTERM]:
        loop.add_signal_handler(signal, lambda: asyncio.ensure_future(cleanup()))

    try:
        loop.run_forever()
    finally:
        loop.close()
