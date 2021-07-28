"""Tests the RemoteFrameBuffer widget class.

We don't test it live (in a notebook) here, but other than that these
tests are pretty complete to test the Python-side logic.
"""

import time

import numpy as np
from pytest import raises
from jupyter_rfb.widget import RemoteFrameBuffer


class MyRFB(RemoteFrameBuffer):

    max_buffered_frames = 1

    _rfb_draw_requested = False

    def __init__(self):
        super().__init__()
        self.frame_feedback = {}
        self.msgs = []

    def send(self, msg):
        self.msgs.append(msg)

    def get_frame(self):
        return np.array([[1, 2], [3, 4]], np.uint8)

    def handle_event(self, event):
        pass

    def trigger(self, request):
        if request:
            self._rfb_draw_requested = True
        self._rfb_maybe_draw()


def test_widget_frames_and_stats_1():

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

    w = RemoteFrameBuffer()
    frame = w.get_frame()
    assert (frame is None) or frame.shape == (1, 1)


def test_requesting_draws():

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

    w = MyRFB()
    events = []
    w.handle_event = lambda event: events.append(event)

    # On closing, an event is emitted
    # Note that when the model is closed from JS, we emit a close event from there.
    w.close()
    assert len(events) == 1 and events[0]["event_type"] == "close"


if __name__ == "__main__":
    test_widget_frames_and_stats_1()
    test_widget_frames_and_stats_3()
    test_get_frame_can_be_none()
    test_widget_traits()
    test_widget_default_get_frame()
    test_requesting_draws()
    test_automatic_events()
