import time

import numpy as np

from jupyter_rfb.widget import FrameSenderMixin


class MyFrameSender(FrameSenderMixin):

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

    def trigger(self, request):
        if request:
            self._rfb_draw_requested = True
        self._rfb_maybe_draw()


def test_framesender_1():

    fs = MyFrameSender()
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


def test_framesender_3():

    fs = MyFrameSender()
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


if __name__ == "__main__":
    test_framesender_1()
    test_framesender_3()
