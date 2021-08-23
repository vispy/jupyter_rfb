"""Tests the RemoteFrameBuffer widget class.

We don't test it live (in a notebook) here, but other than that these
tests are pretty complete to test the Python-side logic.
"""

import time

import numpy as np
from pytest import raises
from jupyter_rfb import RemoteFrameBuffer
from jupyter_rfb._utils import Snapshot


class MyRFB(RemoteFrameBuffer):
    """RFB class to use in the tests."""

    max_buffered_frames = 1

    _rfb_draw_requested = False

    def __init__(self):
        super().__init__()
        self.frame_feedback = {}
        self.msgs = []

    def send(self, msg):
        """Overload the send method so we can check what was sent."""
        self.msgs.append(msg)

    def get_frame(self):
        """Return a stub array."""
        return np.array([[1, 2], [3, 4]], np.uint8)

    def handle_event(self, event):
        """Implement to do nothing.

        Just to make sure that some events that are automatically sent
        dont rely on the super to be called.
        """
        pass

    def trigger(self, request):
        """Simulate an "event loop iteration", optionally request a new draw."""
        if request:
            self._rfb_draw_requested = True
        self._rfb_maybe_draw()


def test_widget_frames_and_stats_1():
    """Test sending frames with max 1 in-flight, and how it affects stats."""

    fs = MyRFB()
    fs.max_buffered_frames = 1

    assert len(fs.msgs) == 0

    # Request a draw
    fs.trigger(True)
    assert len(fs.msgs) == 1

    # Request another, no draw yet, because previous one is not yet confirmed
    fs.trigger(True)
    fs.trigger(True)
    fs.trigger(True)
    assert len(fs.msgs) == 1

    assert fs.get_stats()["sent_frames"] == 1
    assert fs.get_stats()["confirmed_frames"] == 0

    # Flush
    fs.frame_feedback["index"] = 1
    fs.frame_feedback["timestamp"] = fs.msgs[-1]["timestamp"]
    fs.frame_feedback["localtime"] = time.time()

    # Trigger, the previous request is still open
    fs.trigger(False)
    assert len(fs.msgs) == 2

    assert fs.get_stats()["sent_frames"] == 2
    assert fs.get_stats()["confirmed_frames"] == 1

    # Flush
    fs.frame_feedback["index"] = 2
    fs.frame_feedback["timestamp"] = fs.msgs[-1]["timestamp"]
    fs.frame_feedback["localtime"] = time.time()

    fs.trigger(False)
    assert len(fs.msgs) == 2

    assert fs.get_stats()["sent_frames"] == 2
    assert fs.get_stats()["confirmed_frames"] == 2

    # Trigger with no request do not trigger a draw
    # We *can* draw but *should* not.
    fs.trigger(False)
    assert len(fs.msgs) == 2

    assert fs.get_stats()["sent_frames"] == 2
    assert fs.get_stats()["confirmed_frames"] == 2

    # One more draw
    fs.trigger(True)
    assert len(fs.msgs) == 3

    assert fs.get_stats()["sent_frames"] == 3
    assert fs.get_stats()["confirmed_frames"] == 2


def test_widget_frames_and_stats_3():
    """Test sending frames with max 3 in-flight, and how it affects stats."""

    fs = MyRFB()
    fs.max_buffered_frames = 3

    assert len(fs.msgs) == 0

    # 1 Send a frame
    fs.trigger(True)
    assert len(fs.msgs) == 1

    # 2 Send a frame
    fs.trigger(True)
    assert len(fs.msgs) == 2

    # 3 Send a frame
    fs.trigger(True)
    assert len(fs.msgs) == 3

    # 4 Send a frame - no draw, because first (3 frames ago) is no confirmed
    fs.trigger(True)
    assert len(fs.msgs) == 3

    assert fs.get_stats()["sent_frames"] == 3
    assert fs.get_stats()["confirmed_frames"] == 0

    # Flush
    fs.frame_feedback["index"] = 3
    fs.frame_feedback["timestamp"] = fs.msgs[-1]["timestamp"]
    fs.frame_feedback["localtime"] = time.time()

    # Trigger with True. We request a new frame, but there was a request open
    fs.trigger(True)
    assert len(fs.msgs) == 4

    assert fs.get_stats()["sent_frames"] == 4
    assert fs.get_stats()["confirmed_frames"] == 3

    # Flush
    fs.frame_feedback["index"] = 4
    fs.frame_feedback["timestamp"] = fs.msgs[-1]["timestamp"]
    fs.frame_feedback["localtime"] = time.time()

    # Trigger, but nothing to send (no frame pending)
    fs.trigger(False)
    assert len(fs.msgs) == 4

    assert fs.get_stats()["sent_frames"] == 4
    assert fs.get_stats()["confirmed_frames"] == 4

    # We can but should not do a draw
    fs.trigger(False)
    assert len(fs.msgs) == 4

    # Do three more draws
    fs.trigger(True)
    fs.trigger(True)
    fs.trigger(True)
    assert len(fs.msgs) == 7

    # And request another (but this one will have to wait)
    fs.trigger(True)
    assert len(fs.msgs) == 7

    # Flush
    fs.frame_feedback["index"] = 7
    fs.frame_feedback["timestamp"] = fs.msgs[-1]["timestamp"]
    fs.frame_feedback["localtime"] = time.time()

    # Trigger with False. no new request, but there was a request open
    fs.trigger(False)
    assert len(fs.msgs) == 8


def test_get_frame_can_be_none():
    """Test that the frame can be None to cancel a draw."""
    w = MyRFB()
    w.max_buffered_frames = 1

    # Make get_frame() return None
    w.get_frame = lambda: None

    assert len(w.msgs) == 0

    # Request a draw
    w.trigger(True)
    assert len(w.msgs) == 0

    # Request another
    w.trigger(True)
    w.trigger(True)
    assert len(w.msgs) == 0

    assert w.get_stats()["sent_frames"] == 0
    assert w.get_stats()["confirmed_frames"] == 0


def test_widget_traits():
    """Test the widget's traits default values."""

    w = RemoteFrameBuffer()

    assert w.frame_feedback == {}

    assert w.max_buffered_frames == 2
    w.max_buffered_frames = 99
    w.max_buffered_frames = 1
    with raises(Exception):  # TraitError -> min 1
        w.max_buffered_frames = 0

    assert w.css_width.endswith("px")
    assert w.css_height.endswith("px")

    assert w.resizable


def test_widget_default_get_frame():
    """Test default return value of get_frame()."""

    w = RemoteFrameBuffer()
    frame = w.get_frame()
    assert (frame is None) or frame.shape == (1, 1)


def test_requesting_draws():
    """Test that requesting draws works as intended."""

    # By default no frame is requested
    w = RemoteFrameBuffer()
    assert not w._rfb_draw_requested

    # Call request_draw to request a draw
    w._rfb_draw_requested = False
    w.request_draw()
    assert w._rfb_draw_requested

    # On a resize event, a frame is requested too
    w._rfb_draw_requested = False
    w._rfb_handle_msg(None, {"event_type": "resize"}, [])
    assert w._rfb_draw_requested


def test_automatic_events():
    """Test that some events are indeed emitted automatically."""

    w = MyRFB()
    events = []
    w.handle_event = lambda event: events.append(event)

    # On closing, an event is emitted
    # Note that when the model is closed from JS, we emit a close event from there.
    w.close()
    assert len(events) == 1 and events[0]["event_type"] == "close"


def test_print():
    """Test that the widget has a fully featured print method."""
    w = MyRFB()
    w.print("foo bar", sep="-", end=".")
    # mmm, a bit hard to see where the data has ended up,
    # but if it did not error, that's something!
    # We test the printing itself in test_utils.py


def test_snapshot():
    """Test that the widget has a snapshot method that produces a Snapshot."""
    w = MyRFB()
    s = w.snapshot()
    assert isinstance(s, Snapshot)
    assert np.all(s.data == w.get_frame())
