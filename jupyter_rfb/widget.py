"""

See widget.js for the client counterpart to this file.

## Developer notes

The server sends frames to the client, and the client sends back
a confirmation when it has processed the frame.

The server will not send more than `max_buffered_frames` beyond the
last confirmed frame. As such, if the client processes frames slower,
the server will slow down too. The server can also queue frames, at
most max_queued_frames. The use case for this is probably limited to
stress-tests. Both values should probably just be 1.
"""

import time
from base64 import encodebytes

import ipywidgets as widgets
from traitlets import Unicode, Dict, Int, Bool
from ._png import array2png


class FrameSenderMixin:

    # This mixin needs from a subclass:
    # .frame_feedback
    # .max_buffered_frames
    # .max_queued_frames
    # .send()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._frame_index = 0
        self._frame_index_roundtrip = 0
        self._pending_frames = []
        self.reset_stats()

    def reset_stats(self):
        """Reset the stats (start measuring from this point in time)."""
        self._stats = {
            "start_index": self._frame_index,
            "start_time": time.time(),
            "last_confirmed_time": 0,
            "received_frames": 0,
            "sent_frames": 0,
            "confirmed_frames": 0,
            "dropped_frames": 0,
            "roundtrip_count": 0,
            "roundtrip_sum": 0,
            "delivery_sum": 0,
            "img_encoding_sum": 0,
            "b64_encoding_sum": 0,
        }

    @property
    def stats(self):
        """Get the current stats since the last time ``reset_stats()``
        was called. Stats is a dict with the following fields:

        * received_frames: the number of frames reveived for sending.
        * sent_frames: the number of frames actually sent. Some frames may have
          been dropped, or simply not sent yet.
        * confirmed_frames: number of frames confirmed to be reveived at the client.
        * roundtrip: avererage time for processing one frame, including receiver confirmation.
        * delivery: average time for processing one frame until receival by the client.
          This measure assumes that the clock of the server and client are precisely synced.
        * img_encoding: the average time spent on encoding the array into an image (PNG).
        * b64_encoding: the average time spent on base64 encoding the data.
        * fps: the average FPS, measures by deviding the number of confirmed
          frames by the run-time, where run-time is the time from the moment
          ``reset_stats()`` is called, until the last frame confirmation.

        """
        d = self._stats
        fps = d["confirmed_frames"] / (
            d["last_confirmed_time"] - d["start_time"] + 0.00001
        )
        sent_frames_div = d["sent_frames"] or 1
        roundtrip_count_div = d["roundtrip_count"] or 1
        return {
            "received_frames": d["received_frames"],
            "sent_frames": d["sent_frames"],
            "confirmed_frames": d["confirmed_frames"],
            "dropped_frames": d["dropped_frames"],
            "roundtrip": d["roundtrip_sum"] / roundtrip_count_div,
            "delivery": d["delivery_sum"] / roundtrip_count_div,
            "img_encoding": d["img_encoding_sum"] / sent_frames_div,
            "b64_encoding": d["b64_encoding_sum"] / sent_frames_div,
            "fps": fps,
        }

    def send_frame(self, array):
        """Schedule a frame to be send the browser. The frame may be
        send immediately, or queued to be send slightly later.

        When a frame is received by the client, it will confirm the
        receival. A total of ``max_buffered_frames`` can be "in-flight",
        i.e. sent but not not yet confirmed. If ``send_frame()`` is
        called while the queue (frames waiting to be send) exceeds
        ``max_queued_frames``, the oldest frames will be dropped.
        """
        self._stats["received_frames"] += 1
        n_queued = len(self._pending_frames)
        max_queued = max(1, self.max_queued_frames) - 1  # -1 because we'll add one
        if n_queued > max_queued:
            self._stats["dropped_frames"] += n_queued - max_queued
            self._pending_frames[max_queued:] = []
        self._pending_frames.append(array)
        self._iter()

    def _iter(self, *args):
        # Called when trying to send a frame,
        # and every time that we receive new frame_feedback from the model
        frame_feedback = self.frame_feedback
        last_index = frame_feedback.get("index", 0)
        # Send frames if we can
        max_buffered = max(0, self.max_buffered_frames)
        while self._pending_frames and last_index > self._frame_index - max_buffered:
            self._send_frame(self._pending_frames.pop(0))
        # Update stats (note that we may not get an update for each and every drame
        if last_index > self._frame_index_roundtrip:
            self._frame_index_roundtrip = last_index
            self._stats["confirmed_frames"] = last_index - self._stats["start_index"]
            self._stats["roundtrip_count"] += 1
            self._stats["roundtrip_sum"] += time.time() - frame_feedback["timestamp"]
            self._stats["delivery_sum"] += (
                frame_feedback["localtime"] - frame_feedback["timestamp"]
            )
            self._stats["last_confirmed_time"] = time.time()

    def _send_frame(self, array):
        """Actually send a frame over to the client."""
        self._frame_index += 1
        self._stats["sent_frames"] += 1
        timestamp = time.time()

        # Turn array into a based64-encoded PNG
        t1 = time.perf_counter()
        png_data = array2png(array)
        t2 = time.perf_counter()
        preamble = "data:image/png;base64,"
        src = preamble + encodebytes(png_data).decode()
        t3 = time.perf_counter()

        self._stats["img_encoding_sum"] += t2 - t1
        self._stats["b64_encoding_sum"] += t3 - t2

        # Compose message and send
        msg = dict(
            type="framebufferdata",
            src=src,
            index=self._frame_index,
            timestamp=timestamp,
        )
        self.send(msg)


@widgets.register
class RemoteFrameBuffer(FrameSenderMixin, widgets.DOMWidget):
    """Widget that shows a remote frame buffer."""

    # Name of the widget view class in front-end
    _view_name = Unicode("RemoteFrameBufferView").tag(sync=True)

    # Name of the widget model class in front-end
    _model_name = Unicode("RemoteFrameBufferModel").tag(sync=True)

    # Name of the front-end module containing widget view
    _view_module = Unicode("jupyter_rfb").tag(sync=True)

    # Name of the front-end module containing widget model
    _model_module = Unicode("jupyter_rfb").tag(sync=True)

    # Version of the front-end module containing widget view
    _view_module_version = Unicode("^0.1.0").tag(sync=True)
    # Version of the front-end module containing widget model
    _model_module_version = Unicode("^0.1.0").tag(sync=True)

    # Widget specific properties
    frame_feedback = Dict({}).tag(sync=True)
    max_buffered_frames = Int(1, min=1)
    max_queued_frames = Int(1, min=1)

    css_width = Unicode("100%").tag(sync=True)
    css_height = Unicode("300px").tag(sync=True)
    resizable = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_msg(self._receive_events)
        self.observe(self._iter, names=["frame_feedback"])

    def _receive_events(self, widget, content, buffers):
        pass
        # print(content)
        # if content['msg_type'] == 'init':
        #     self.canvas_backend._reinit_widget()
        # elif content['msg_type'] == 'events':
        #     events = content['contents']
        #     for ev in events:
        #         self.gen_event(ev)
        # elif content['msg_type'] == 'status':
        #     if content['contents'] == 'removed':
        #         # Stop all timers associated to the widget.
        #         _stop_timers(self.canvas_backend._vispy_canvas)
