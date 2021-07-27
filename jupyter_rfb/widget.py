"""

See widget.js for the client counterpart to this file.

## Developer notes

The server sends frames to the client, and the client sends back
a confirmation when it has processed the frame.

The server will not send more than *max_buffered_frames* beyond the
last confirmed frame. As such, if the client processes frames slower,
the server will slow down too.
"""

import asyncio
import time
from base64 import encodebytes

import ipywidgets
import numpy as np
from traitlets import Bool, Dict, Int, Unicode

from ._png import array2png


class FrameSenderMixin:
    """Mixin class that contains the logic for sending frames and keeping
    track of stats. By making this a mixin, it is much easier to unit-test.
    """

    # This mixin needs from a subclass:
    # .frame_feedback
    # .max_buffered_frames
    # .get_frame()
    # .send()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rfb_frame_index = 0
        self._rfb_last_confirmed_index = 0
        self.reset_stats()

    def reset_stats(self):
        """Reset the stats (start measuring from this point in time).
        Note that the FPS measurement starts on the first frame drawn
        after this call.
        """
        self._rfb_stats = {
            "start_time": 0,
            "last_time": 1,
            "sent_frames": 0,
            "confirmed_frames": 0,
            "roundtrip_count": 0,
            "roundtrip_sum": 0,
            "delivery_sum": 0,
            "img_encoding_sum": 0,
            "b64_encoding_sum": 0,
        }

    def get_stats(self):
        """Get the current stats since the last time ``reset_stats()``
        was called. Stats is a dict with the following fields:

        * *sent_frames*: the number of frames sent.
        * *confirmed_frames*: number of frames confirmed to be reveived by the client.
        * *roundtrip*: avererage time for processing a frame, including receiver confirmation.
        * *delivery*: average time for processing a frame until it's received by the client.
          This measure assumes that the clock of the server and client are precisely synced.
        * *img_encoding*: the average time spent on encoding the array into an image.
        * *b64_encoding*: the average time spent on base64 encoding the data.
        * *fps*: the average FPS, measured by deviding the number of confirmed
          frames by the run-time, where run-time is the time from when the first
          frame was sent (since ``reset_stats()`` was called), until the last
          frame was confirmed.
        """
        d = self._rfb_stats
        roundtrip_count_div = d["roundtrip_count"] or 1
        sent_frames_div = d["sent_frames"] or 1
        fps_div = (d["last_time"] - d["start_time"]) or 0.001
        return {
            "sent_frames": d["sent_frames"],
            "confirmed_frames": d["confirmed_frames"],
            "roundtrip": d["roundtrip_sum"] / roundtrip_count_div,
            "delivery": d["delivery_sum"] / roundtrip_count_div,
            "img_encoding": d["img_encoding_sum"] / sent_frames_div,
            "b64_encoding": d["b64_encoding_sum"] / sent_frames_div,
            "fps": d["confirmed_frames"] / fps_div,
        }

    def _rfb_update_stats(self, feedback):
        """Update the stats when a new frame feedback has arrived."""
        last_index = feedback.get("index", 0)
        if last_index > self._rfb_last_confirmed_index:
            timestamp = feedback["timestamp"]
            nframes = last_index - self._rfb_last_confirmed_index
            self._rfb_last_confirmed_index = last_index
            self._rfb_stats["confirmed_frames"] += nframes
            self._rfb_stats["roundtrip_count"] += 1
            self._rfb_stats["roundtrip_sum"] += time.time() - timestamp
            self._rfb_stats["delivery_sum"] += feedback["localtime"] - timestamp
            self._rfb_stats["last_time"] = time.time()
            if not self._rfb_stats["start_time"]:
                self._rfb_stats["start_time"] = timestamp

    def _rfb_maybe_draw(self):
        """Perform a draw, if we can and should."""
        feedback = self.frame_feedback
        self._rfb_update_stats(feedback)
        last_index = feedback.get("index", 0)
        max_buffered = max(0, self.max_buffered_frames)
        if (
            self._rfb_draw_requested
            and last_index > self._rfb_frame_index - max_buffered
        ):
            self._rfb_draw_requested = False
            array = self.get_frame()
            if array is not None:
                self._rfb_send_frame(array)

    def _rfb_send_frame(self, array):
        """Actually send a frame over to the client."""
        self._rfb_frame_index += 1
        timestamp = time.time()

        # Turn array into a based64-encoded PNG
        t1 = time.perf_counter()
        png_data = array2png(array)
        t2 = time.perf_counter()
        preamble = "data:image/png;base64,"
        src = preamble + encodebytes(png_data).decode()
        t3 = time.perf_counter()

        # Stats
        self._rfb_stats["img_encoding_sum"] += t2 - t1
        self._rfb_stats["b64_encoding_sum"] += t3 - t2
        self._rfb_stats["sent_frames"] += 1

        # Compose message and send
        msg = dict(
            type="framebufferdata",
            src=src,
            index=self._rfb_frame_index,
            timestamp=timestamp,
        )
        self.send(msg)


@ipywidgets.register
class RemoteFrameBuffer(FrameSenderMixin, ipywidgets.DOMWidget):
    """A widget that shows a remote frame buffer.
    Subclass of `ipywidgets.DOMWidget <https://ipywidgets.readthedocs.io>`_.

    This widget has the following traits:

    * *css_width*: the logical width of the frame as a CSS string. Default '100%'.
    * *css_height*: the logical height of the frame as a CSS string. Default '300xp'.
    * *resizable*: whether the frame can be manually resized. Default True.
    * *max_buffered_frames*: the number of frames that is allowed to be "in-flight",
      i.e. sent, but not yet confirmed by the client. Default 2. Higher values
      may result in a higher FPS at the cost of introducing lag.

    To use this class, it should be subclassed, and its ``get_frame()``
    and ``handle_event()`` methods should be implemented.
    """

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

    # Widget specific traits
    frame_feedback = Dict({}).tag(sync=True)
    max_buffered_frames = Int(2, min=1)
    css_width = Unicode("100%").tag(sync=True)
    css_height = Unicode("300px").tag(sync=True)
    resizable = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rfb_draw_requested = False
        self.on_msg(self._rfb_handle_msg)
        self.observe(self._rfb_schedule_maybe_draw, names=["frame_feedback"])

    def _rfb_handle_msg(self, widget, content, buffers):
        """Receive custom messages and filter our events."""
        if "event_type" in content:
            if content["event_type"] == "resize":
                self.request_draw()
            self.handle_event(content)

    def _rfb_schedule_maybe_draw(self, *args):
        """Schedule _maybe_draw() to be called in a fresh event loop iteration."""
        loop = asyncio.get_event_loop()
        loop.call_soon(self._rfb_maybe_draw)
        # or
        # ioloop = tornado.ioloop.IOLoop.current()
        # ioloop.add_callback(self._rfb_maybe_draw)

    def request_draw(self):
        """Schedule a new draw when the widget is ready for it. During
        a draw, the ``get_frame()`` method is called, and the resulting
        array is sent to the client. This method is automatically called
        on each resize event.
        """
        # Technically, _maybe_draw() may not perform a draw if there are too
        # many frames in-flight. But in this case, we'll eventually get
        # new frame_feedback, which will then trigger a draw.
        if not self._rfb_draw_requested:
            self._rfb_draw_requested = True
            self._rfb_schedule_maybe_draw()

    def close(self, *args, **kwargs):
        # When the widget is closed, we notify by creating a close event. The
        # same event is emitted from JS when the model is closed in the client.
        super().close(*args, **kwargs)
        self._rfb_handle_msg(self, {"event_type": "close"}, [])

    def get_frame(self):
        """The method that is called during a draw to obtain a new
        frame. Subclasses should overload this. May return ``None`` to
        cancel the draw.
        """
        return np.ones((1, 1), np.uint8) * 127

    def handle_event(self, event):
        """The method that is called on each event. Overload this to process
        incoming events. An event is a dict with at least the key *event_type*.
        See the docs of ``jupyter_rfb.events`` for details.
        """
        pass
