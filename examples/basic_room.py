import asyncio
import logging
from signal import SIGINT, SIGTERM
from typing import Union
import os

from livekit import api, rtc

import cv2
import numpy as np
from livekit.rtc import VideoFrame, VideoStream
from livekit.rtc._proto import video_frame_pb2 as proto_video

# ensure LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET are set


async def main(room: rtc.Room) -> None:
    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant) -> None:
        logging.info(
            "participant connected: %s %s", participant.sid, participant.identity
        )

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        logging.info(
            "participant disconnected: %s %s", participant.sid, participant.identity
        )

    @room.on("local_track_published")
    def on_local_track_published(
        publication: rtc.LocalTrackPublication,
        track: Union[rtc.LocalAudioTrack, rtc.LocalVideoTrack],
    ):
        logging.info("local track published: %s", publication.sid)

    @room.on("active_speakers_changed")
    def on_active_speakers_changed(speakers: list[rtc.Participant]):
        logging.info("active speakers changed: %s", speakers)

    @room.on("local_track_unpublished")
    def on_local_track_unpublished(publication: rtc.LocalTrackPublication):
        logging.info("local track unpublished: %s", publication.sid)

    @room.on("track_published")
    def on_track_published(
        publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant
    ):
        logging.info(
            "track published: %s from participant %s (%s)",
            publication.sid,
            participant.sid,
            participant.identity,
        )

    @room.on("track_unpublished")
    def on_track_unpublished(
        publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant
    ):
        logging.info("track unpublished: %s", publication.sid)

    # async def receive_frames(stream: rtc.VideoStream):
    #     async for frame in stream:
    #         # received a video frame from the track, process it here
    #         #Display the frame in a local window
    #         pass

    async def receive_frames(stream: VideoStream):
        async for video_event in stream:
            frame: VideoFrame = video_event.frame

            # Extract frame data and reshape to the frame's dimensions
            frame_data = np.array(frame.data)  # Convert memoryview to NumPy array

            # Handle pixel formats
            if frame.type == proto_video.VideoBufferType.RGBA:
                frame_reshaped = frame_data.reshape((frame.height, frame.width, 4))  # RGBA
                frame_bgr = cv2.cvtColor(frame_reshaped, cv2.COLOR_RGBA2BGR)  # Convert RGBA to BGR
            elif frame.type == proto_video.VideoBufferType.RGB24:
                frame_reshaped = frame_data.reshape((frame.height, frame.width, 3))  # RGB
                frame_bgr = cv2.cvtColor(frame_reshaped, cv2.COLOR_RGB2BGR)  # Convert RGB to BGR
            # elif frame.type == proto_video.VideoBufferType.I420:
            #     y_size = frame.height * frame.width
            #     uv_size = (frame.height // 2) * (frame.width // 2)
            #     y_plane = frame_data[:y_size]
            #     uv_plane = frame_data[y_size:]
            #     y_reshaped = y_plane.reshape((frame.height, frame.width))
            #     uv_reshaped = uv_plane.reshape((frame.height // 2, frame.width // 2, 2))
            #     frame_bgr = cv2.cvtColor(y_reshaped, cv2.COLOR_YUV2BGR_I420)
            elif frame.type == proto_video.VideoBufferType.I420:
                # OpenCV expects the full YUV I420 data as a single array
                yuv_data = frame_data.reshape((frame.height * 3) // 2, frame.width)
                frame_bgr = cv2.cvtColor(yuv_data, cv2.COLOR_YUV2BGR_I420)
            else:
                print(f"Unsupported video frame format: {frame.type}")
                continue

            # Display the frame using OpenCV
            cv2.imshow("Live Video", frame_bgr)

            # Allow OpenCV to process GUI events and handle key press
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        # Cleanup OpenCV windows after the stream ends
        cv2.destroyAllWindows()

    @room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        logging.info("track subscribed: %s", publication.sid)
        if track.kind == rtc.TrackKind.KIND_VIDEO:
            _video_stream = rtc.VideoStream(track)
            # video_stream is an async iterator that yields VideoFrame
            asyncio.ensure_future(receive_frames(_video_stream))
        elif track.kind == rtc.TrackKind.KIND_AUDIO:
            print("Subscribed to an Audio Track")
            _audio_stream = rtc.AudioStream(track)
            # audio_stream is an async iterator that yields AudioFrame

    @room.on("track_unsubscribed")
    def on_track_unsubscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        logging.info("track unsubscribed: %s", publication.sid)

    @room.on("track_muted")
    def on_track_muted(
        publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant
    ):
        logging.info("track muted: %s", publication.sid)

    @room.on("track_unmuted")
    def on_track_unmuted(
        publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant
    ):
        logging.info("track unmuted: %s", publication.sid)

    @room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        logging.info("received data from %s: %s", data.participant.identity, data.data)

    @room.on("connection_quality_changed")
    def on_connection_quality_changed(
        participant: rtc.Participant, quality: rtc.ConnectionQuality
    ):
        logging.info("connection quality changed for %s", participant.identity)

    @room.on("track_subscription_failed")
    def on_track_subscription_failed(
        participant: rtc.RemoteParticipant, track_sid: str, error: str
    ):
        logging.info("track subscription failed: %s %s", participant.identity, error)

    @room.on("connection_state_changed")
    def on_connection_state_changed(state: rtc.ConnectionState):
        logging.info("connection state changed: %s", state)

    @room.on("connected")
    def on_connected() -> None:
        logging.info("connected")

    @room.on("disconnected")
    def on_disconnected() -> None:
        logging.info("disconnected")

    @room.on("reconnecting")
    def on_reconnecting() -> None:
        logging.info("reconnecting")

    @room.on("reconnected")
    def on_reconnected() -> None:
        logging.info("reconnected")

    # token = (
    #     api.AccessToken()
    #     .with_identity("python-bot")
    #     .with_name("Python Bot")
    #     .with_grants(
    #         api.VideoGrants(
    #             room_join=True,
    #             room="my-room",
    #         )
    #     )
    #     .to_jwt()
    # )

    token = os.getenv("LIVEKIT_TOKEN")
    await room.connect(os.getenv("LIVEKIT_URL"), token)
    logging.info("connected to room %s", room.name)
    logging.info("participants: %s", room.remote_participants)

    await asyncio.sleep(2)
    await room.local_participant.publish_data("hello world")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logging.FileHandler("basic_room.log"), logging.StreamHandler()],
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

