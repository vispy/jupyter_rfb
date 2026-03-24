"""

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
from importlib.resources import files as resource_files

import anywidget
import numpy as np
from IPython.display import display
from traitlets import Bool, Dict, Int, Unicode

from ._utils import array2compressed, RFBOutputContext, Snapshot


def _load_js_and_css():
    js = ""
    for fname in ["renderview.js", "renderview-rfb.js"]:
        js_path = resource_files("jupyter_rfb").joinpath(fname)
        js += js_path.read_text() + "\n\n"

    css_path = resource_files("jupyter_rfb").joinpath("renderview.css")

    return js, css_path.read_text()


JS, CSS = _load_js_and_css()


class RemoteFrameBuffer(anywidget.AnyWidget):
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
    * *cursor*: the cursor style, ex: "crosshair", "grab". Valid cursors:
      https://developer.mozilla.org/en-US/docs/Web/CSS/cursor#keyword

    """

    _esm = JS
    _css = CSS

    # A bitmask, allowing subclasses to determine the events that they receive
    # 1: old events (jupyter rfb spec, with 'event_type', 'time_stamp', 'pixel_ratio')
    # 2: new style events (with 'type', 'timestamp', 'ratio')
    # 3: both
    # TODO: about a year after vispy and rendercanvas had a release that was compatible with the new style, drop the compatibility
    _event_compatibility = None

    # Widget specific traits
    _frame_feedback = Dict({}).tag(sync=True)
    _has_visible_views = Bool(False).tag(sync=True)
    max_buffered_frames = Int(2, min=1)
    quality = Int(80, min=1, max=100)
    css_width = Unicode("500px").tag(sync=True)
    css_height = Unicode("300px").tag(sync=True)
    resizable = Bool(True).tag(sync=True)
    cursor = Unicode("default").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default event compatibility. Default is 3, or 1 for PyGfx (bc it errors when both 'type' and 'event_type' are present)
        if self._event_compatibility is None:
            self._event_compatibility = 3
            if any(
                cls.__module__.startswith("rendercanvas")
                for cls in self.__class__.mro()
            ):
                self._event_compatibility = 1
        # Setup an output widget, so that any errors in our callbacks
        # are actually shown. We display the output in the cell-output
        # corresponding to the cell that instantiates the widget.
        self._output_context = RFBOutputContext()
        display(self._output_context)
        # Init attributes for drawing
        self._rfb_last_frame = None
        self._rfb_displayed_with_handle = False
        self._rfb_pending_display = None
        self._rfb_draw_requested = False
        self._rfb_frame_index = 0
        self._rfb_last_confirmed_index = 0
        self._rfb_last_resize_event = None
        self._rfb_warned_png = False
        self._rfb_lossless_draw_info = None
        self._use_websocket = True  # Could be a prop, private for now
        # Init stats
        self.reset_stats()
        # Setup events
        self.on_msg(self._rfb_handle_msg)
        self.observe(
            self._rfb_schedule_maybe_draw,
            names=["_frame_feedback", "_has_visible_views"],
        )

    def _repr_mimebundle_(self, **kwargs):
        # This is a bit of a dirty trick. On the first time that this is called,
        # we assume that this is because we are displayed, e.g. because the
        # canvas is the last expression in a cell. Instead of returning the
        # expected data, we call display() and return None. That provides as
        # with a display handle, that we can use to replace the display once we
        # receive the first frame.
        if not self._rfb_displayed_with_handle:
            self._rfb_displayed_with_handle = True
            self._rfb_pending_display = display(self, display_id=True)
            return None

        # Use default
        result = anywidget.AnyWidget._repr_mimebundle_(self, **kwargs)
        # Get dict to add more data
        data = None
        if isinstance(result, tuple):
            data = result[0]
        elif isinstance(result, dict):
            data = result
        # Add initial snapshot if we have it
        if data and self._rfb_last_frame is not None:
            data["text/html"] = self.snapshot()._repr_html_()
            self._rfb_pending_display = None  # no need to reload
        return result

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
        anywidget.AnyWidget.close(self, *args, **kwargs)
        self._rfb_handle_msg(self, {"type": "close", "event_type": "close"}, [])

    def _rfb_handle_msg(self, widget, content, buffers):
        """Receive custom messages and filter our events."""
        if "type" in content:
            event = content

            # We have some builtin handling
            if event["type"] == "resize":
                self._rfb_last_resize_event = event
                self.request_draw()
            elif event["type"] == "close":
                self._rfb_last_frame = None
                self._rfb_displayed_with_handle = True
            # Turn lists into tuples (js/json does not have tuples)
            if "buttons" in event:
                event["buttons"] = tuple(event["buttons"])
            if "modifiers" in event:
                event["modifiers"] = tuple(event["modifiers"])

            # Handle backwards compatibility
            if self._event_compatibility & 1:  # 1 or 3
                old_event = event
                event = {"event_type": old_event["type"]}
                event.update(old_event)
                event["time_stamp"] = event.get("timestamp", 0)
                if "ratio" in event:
                    event["pixel_ratio"] = event["ratio"]
                if self._event_compatibility == 1:
                    event.pop("type", None)
                    event.pop("timestamp", None)
                    event.pop("ratio", None)

            # Let the subclass handle the event
            with self._output_context:
                self.handle_event(event)

    # ---- drawing

    def snapshot(self, pixel_ratio=None):
        """Create a snapshot of the current state of the widget.

        Returns an ``IPython DisplayObject`` that can simply be used as
        a cell output. The display object has a ``data`` attribute that holds
        the image array data (typically a numpy array).

        The ``pixel_ratio`` argument is deprecated and ignored.
        """
        # Get the current size
        ref_resize_event = self._rfb_last_resize_event
        if ref_resize_event:
            w = ref_resize_event["width"]
            h = ref_resize_event["height"]
        else:
            css_width, css_height = self.css_width, self.css_height
            w = float(css_width[:-2]) if css_width.endswith("px") else 500
            h = float(css_height[:-2]) if css_height.endswith("px") else 300
        # Get last frame or single-pixel image
        array = self._rfb_last_frame
        if array is None:
            array = np.ones((1, 1, 3), np.uint8) * 127
        # Super-weird, but it looks like nbsphinx only selects the text/html field when we use a css class
        # that starts with 'snapshot-'. Is this some upstream hack to make jupyter-rfb work, that we don't know of?
        return Snapshot(array, w, h, "snapshot", f"snapshot-rfb model{self._model_id}")

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

    def send_frame(self, array):
        """Send a frame to display.

        The intended use is for async use-cases, to let ``get_frame()`` return
        None, render the frame asynchronously, and use ``send_frame()`` when its
        done.

        This function *can* be used to push frames to the client, but this is
        not recommended in general, since it bypasses the frame throughput
        mechanism, and can therefore overload the IO, resulting in high latency.
        """
        self._rfb_send_frame(array)

    def _rfb_schedule_maybe_draw(self, *args):
        """Schedule _maybe_draw() to be called in a fresh event loop iteration."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.call_soon(self._rfb_maybe_draw)

    def _rfb_maybe_draw(self):
        """Perform a draw, if we can and should."""
        feedback = self._frame_feedback
        # Update stats
        self._rfb_update_stats(feedback)
        # Determine whether we should perform a draw: a draw was requested, and
        # the client is ready for a new frame, and the client widget is visible.
        frames_in_flight = self._rfb_frame_index - feedback.get("index", 0)
        should_draw = (
            self._rfb_draw_requested
            and frames_in_flight < self.max_buffered_frames
            and self._has_visible_views
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
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
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

        # Failsafe
        if array.size == 0:
            return

        quality = 100 if is_lossless_redraw else self.quality

        self._rfb_frame_index += 1
        self._rfb_last_frame = array
        timestamp = time.time()

        # Turn array into a based64-encoded JPEG or PNG
        t1 = time.perf_counter()
        mimetype, data = array2compressed(array, quality)
        if self._use_websocket:
            datas = [data]
            data_b64 = None
        else:
            datas = []
            data_b64 = f"data:{mimetype};base64," + encodebytes(data).decode()
        t2 = time.perf_counter()

        if "jpeg" in mimetype:
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
            self._rfb_stats["sent_frames"] += 1
            if self._rfb_stats["start_time"] <= 0:  # Start measuring
                self._rfb_stats["start_time"] = timestamp
                self._rfb_last_confirmed_index = self._rfb_frame_index - 1

        # Reload the output if we did not have a frame when the widget was first loaded
        if self._rfb_pending_display is not None:
            if self._rfb_last_resize_event is not None:
                self._rfb_pending_display.update(self)  # -> calls _repr_mimebundle_

        # Compose message and send
        msg = dict(
            type="framebufferdata",
            mimetype=mimetype,
            data_b64=data_b64,
            index=self._rfb_frame_index,
            timestamp=timestamp,
        )
        self.send(msg, datas)

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

        As alternative asynchronous usage, the implementation may also return
        None and then call ``send_frame()`` somewhat later.
        """
        return None

    def handle_event(self, event):
        """Handle an incoming event.

        Subclasses should overload this method. Events include widget resize,
        mouse/touch interaction, key events, and more. An event is a dict with at least
        the key *type*. See :mod:`jupyter_rfb.events` for details.
        """
        pass
