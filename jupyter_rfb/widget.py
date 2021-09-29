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
from IPython.display import display
from traitlets import Bool, Dict, Int, Unicode

from ._utils import array2compressed, RFBOutputContext, Snapshot


@ipywidgets.register
class RemoteFrameBuffer(ipywidgets.DOMWidget):
    """A widget implementing a remote frame buffer.

    This is a subclass of `ipywidgets.DOMWidget <https://ipywidgets.readthedocs.io>`_.
    To use this class, it should be subclassed, and its
    :func:`.get_frame() <jupyter_rfb.RemoteFrameBuffer.get_frame>` and
    :func:`.handle_event() <jupyter_rfb.RemoteFrameBuffer.handle_event>`
    methods should be implemented.

    This widget has the following traits:

    * *css_width*: the logical width of the frame as a CSS string. Default '500px'.
    * *css_height*: the logical height of the frame as a CSS string. Default '300px'.
    * *resizable*: whether the frame can be manually resized. Default True.
    * *quality*: the quality of the JPEG encoding during interaction/animation
      as a number between 1 and 100. Default 80. Set to lower numbers for more
      performance on slow connections. Note that each interaction is ended with a
      lossless image (PNG). If set to 100 or if JPEG encoding isn't possible (missing
      pillow or simplejpeg dependencies), then lossless PNGs will always be sent.
    * *max_buffered_frames*: the number of frames that is allowed to be "in-flight",
      i.e. sent, but not yet confirmed by the client. Default 2. Higher values
      may result in a higher FPS at the cost of introducing lag.

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
    has_visible_views = Bool(False).tag(sync=True)
    max_buffered_frames = Int(2, min=1)
    quality = Int(80, min=1, max=100)
    css_width = Unicode("500px").tag(sync=True)
    css_height = Unicode("300px").tag(sync=True)
    resizable = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ipython_display_ = None  # we use _repr_mimebundle_ instread
        # Setup an output widget, so that any errors in our callbacks
        # are actually shown. We display the output in the cell-output
        # corresponding to the cell that instantiates the widget.
        self._output_context = RFBOutputContext()
        display(self._output_context)
        # Init attributes for drawing
        self._rfb_draw_requested = False
        self._rfb_frame_index = 0
        self._rfb_last_confirmed_index = 0
        self._rfb_last_resize_event = None
        self._rfb_warned_png = False
        self._rfb_lossless_draw_info = None
        # Init stats
        self.reset_stats()
        # Setup events
        self.on_msg(self._rfb_handle_msg)
        self.observe(
            self._rfb_schedule_maybe_draw, names=["frame_feedback", "has_visible_views"]
        )

    def _repr_mimebundle_(self, **kwargs):
        data = {}

        # Always add plain text
        plaintext = repr(self)
        if len(plaintext) > 110:
            plaintext = plaintext[:110] + "…"
        data["text/plain"] = plaintext

        # Get the actual representation
        try:
            data.update(super()._repr_mimebundle_(**kwargs))
        except Exception:
            # On 7.6.3 and below, _ipython_display_ is used instead of _repr_mimebundle_.
            # We fill in the widget representation that has been in use for 5+ years.
            data["application/vnd.jupyter.widget-view+json"] = {
                "version_major": 2,
                "version_minor": 0,
                "model_id": self._model_id,
            }

        # Add initial snapshot. It would be awesome if, when the
        # notebook is offline, this representation is used instead of
        # application/vnd.jupyter.widget-view+json. And in fact, Gihub's
        # renderer does this. Unfortunately, nbconvert still selects
        # the widget mimetype.
        # So instead, we display() the snapshot right in front of the
        # actual widget view, and when the widget view is created, it
        # hides the snapshot. Ha! That way, the snapshot is
        # automatically shown when the widget is not loaded!
        if self._view_name is not None:
            # data["text/html"] = self.snapshot()._get_html()
            display(self.snapshot(None, _initial=True))

        return data

    def print(self, *args, **kwargs):
        """Print to the widget's output area (for debugging purposes).

        In Jupyter, print calls that occur in a callback or an asyncio task
        may (depending on your version of the notebook/lab) not be shown.
        Inside :func:`.get_frame() <jupyter_rfb.RemoteFrameBuffer.get_frame>`
        and :func:`.handle_event() <jupyter_rfb.RemoteFrameBuffer.handle_event>`
        you can use this method instead. The signature of this method
        is fully compatible with the builtin print function (except for
        the ``file`` argument).
        """
        self._output_context.print(*args, **kwargs)

    def close(self, *args, **kwargs):
        """Close all views of the widget and emit a close event."""
        # When the widget is closed, we notify by creating a close event. The
        # same event is emitted from JS when the model is closed in the client.
        super().close(*args, **kwargs)
        self._rfb_handle_msg(self, {"event_type": "close"}, [])

    def _rfb_handle_msg(self, widget, content, buffers):
        """Receive custom messages and filter our events."""
        if "event_type" in content:
            # We have some builtin handling
            if content["event_type"] == "resize":
                self._rfb_last_resize_event = content
                self.request_draw()
            elif content["event_type"] == "close":
                self._repr_mimebundle_ = None
            # Let the subclass handle the event
            with self._output_context:
                self.handle_event(content)

    # ---- drawing

    def snapshot(self, pixel_ratio=None, _initial=False):
        """Create a snapshot of the current state of the widget.

        Returns an ``IPython DisplayObject`` that can simply be used as
        a cell output. The display object has a ``data`` attribute that holds
        the image array data (typically a numpy array).

        The ``pixel_ratio`` can optionally be set to influence the resolution.
        By default the widgets' "native" pixel-ratio is used.
        """
        # Get the current size
        ref_resize_event = self._rfb_last_resize_event
        new_pixel_ratio = None
        if ref_resize_event:
            # We know the size from the last resize event
            w = ref_resize_event["width"]
            h = ref_resize_event["height"]
            if pixel_ratio and pixel_ratio != ref_resize_event["pixel_ratio"]:
                new_pixel_ratio = pixel_ratio
        else:
            # There has not been a resize event yet -> guess the size from our traits
            new_pixel_ratio = pixel_ratio or 1
            css_width, css_height = self.css_width, self.css_height
            w = float(css_width[:-2]) if css_width.endswith("px") else 500
            h = float(css_height[:-2]) if css_height.endswith("px") else 300
        # If the new pixel ratio is different from "native", we need to resize first
        if new_pixel_ratio:
            evt = {
                "event_type": "resize",
                "width": w,
                "height": h,
                "pixel_ratio": new_pixel_ratio,
            }
            self.handle_event(evt)
        # Render a frame
        array = self.get_frame()
        # Reset pixel ratio
        if new_pixel_ratio and ref_resize_event:
            self.handle_event(ref_resize_event)
        # Create snapshot object
        if array is None:
            array = np.ones((1, 1), np.uint8) * 127
        if _initial:
            title = "initial snapshot"
            class_name = "initial-snapshot-" + self._model_id
        else:
            title = "snapshot"
            class_name = "snapshot-" + self._model_id
        return Snapshot(array, w, h, title, class_name)

    def request_draw(self):
        """Schedule a new draw. This method itself returns immediately.

        This method is automatically called on each resize event. During
        a draw, the :func:`.get_frame() <jupyter_rfb.RemoteFrameBuffer.get_frame>`
        method is called, and the resulting array is sent to the client.
        See the docs for details about scheduling.
        """
        # Technically, _maybe_draw() may not perform a draw if there are too
        # many frames in-flight. But in this case, we'll eventually get
        # new frame_feedback, which will then trigger a draw.
        if not self._rfb_draw_requested:
            self._rfb_draw_requested = True
            self._rfb_cancel_lossless_draw()
            self._rfb_schedule_maybe_draw()

    def _rfb_schedule_maybe_draw(self, *args):
        """Schedule _maybe_draw() to be called in a fresh event loop iteration."""
        loop = asyncio.get_event_loop()
        loop.call_soon(self._rfb_maybe_draw)
        # or
        # ioloop = tornado.ioloop.IOLoop.current()
        # ioloop.add_callback(self._rfb_maybe_draw)

    def _rfb_maybe_draw(self):
        """Perform a draw, if we can and should."""
        feedback = self.frame_feedback
        # Update stats
        self._rfb_update_stats(feedback)
        # Determine whether we should perform a draw: a draw was requested, and
        # the client is ready for a new frame, and the client widget is visible.
        frames_in_flight = self._rfb_frame_index - feedback.get("index", 0)
        should_draw = (
            self._rfb_draw_requested
            and frames_in_flight < self.max_buffered_frames
            and self.has_visible_views
        )
        # Do the draw if we should.
        if should_draw:
            self._rfb_draw_requested = False
            with self._output_context:
                array = self.get_frame()
                if array is not None:
                    self._rfb_send_frame(array)

    def _rfb_schedule_lossless_draw(self, array, delay=0.3):
        self._rfb_cancel_lossless_draw()
        loop = asyncio.get_event_loop()
        handle = loop.call_later(delay, self._rfb_lossless_draw)
        self._rfb_lossless_draw_info = array, handle

    def _rfb_cancel_lossless_draw(self):
        if self._rfb_lossless_draw_info:
            _, handle = self._rfb_lossless_draw_info
            self._rfb_lossless_draw_info = None
            handle.cancel()

    def _rfb_lossless_draw(self):
        array, _ = self._rfb_lossless_draw_info
        self._rfb_send_frame(array, True)

    def _rfb_send_frame(self, array, is_lossless_redraw=False):
        """Actually send a frame over to the client."""

        # For considerations about performance,
        # see https://github.com/vispy/jupyter_rfb/issues/3

        quality = 100 if is_lossless_redraw else self.quality

        self._rfb_frame_index += 1
        timestamp = time.time()

        # Turn array into a based64-encoded JPEG or PNG
        t1 = time.perf_counter()
        preamble, data = array2compressed(array, quality)
        t2 = time.perf_counter()
        src = preamble + encodebytes(data).decode()
        t3 = time.perf_counter()

        if "jpeg" in preamble:
            self._rfb_schedule_lossless_draw(array)
        else:
            self._rfb_cancel_lossless_draw()
            # Issue png warning?
            if quality < 100 and not self._rfb_warned_png:
                self._rfb_warned_png = True
                self.print(
                    "Warning: No JPEG encoder found, using PNG instead. "
                    + "Install simplejpeg or pillow for better performance."
                )

        if is_lossless_redraw:
            # No stats, also not on the confirmation of this frame
            self._rfb_last_confirmed_index = self._rfb_frame_index
        else:
            # Stats
            self._rfb_stats["img_encoding_sum"] += t2 - t1
            self._rfb_stats["b64_encoding_sum"] += t3 - t2
            self._rfb_stats["sent_frames"] += 1
            if self._rfb_stats["start_time"] <= 0:  # Start measuring
                self._rfb_stats["start_time"] = timestamp
                self._rfb_last_confirmed_index = self._rfb_frame_index - 1

        # Compose message and send
        msg = dict(
            type="framebufferdata",
            src=src,
            index=self._rfb_frame_index,
            timestamp=timestamp,
        )
        self.send(msg)

    # ----- related to stats

    def reset_stats(self):
        """Restart measuring statistics from the next sent frame."""
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
        """Get the current stats since the last time ``.reset_stats()`` was called.

        Stats is a dict with the following fields:

        * *sent_frames*: the number of frames sent.
        * *confirmed_frames*: number of frames confirmed by the client.
        * *roundtrip*: avererage time for processing a frame, including receiver confirmation.
        * *delivery*: average time for processing a frame until it's received by the client.
          This measure assumes that the clock of the server and client are precisely synced.
        * *img_encoding*: the average time spent on encoding the array into an image.
        * *b64_encoding*: the average time spent on base64 encoding the data.
        * *fps*: the average FPS, measured from the first frame sent since ``.reset_stats()``
          was called, until the last confirmed frame.
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

    # ----- for the subclass to implement

    def get_frame(self):
        """Return image array for the next frame.

        Subclasses should overload this method. It is automatically called during a draw.
        The returned numpy array must be NxM (grayscale), NxMx3 (RGB) or NxMx4 (RGBA).
        May also return ``None`` to cancel the draw.
        """
        return np.ones((1, 1), np.uint8) * 127

    def handle_event(self, event):
        """Handle an incoming event.

        Subclasses should overload this method. Events include widget resize,
        mouse/touch interaction, key events, and more. An event is a dict with at least
        the key *event_type*. See :mod:`jupyter_rfb.events` for details.
        """
        pass
