import time

import numpy as np

from jupyter_rfb.widget import FrameSenderMixin


class MyFrameSender(FrameSenderMixin):

    max_buffered_frames = 1
    max_queued_frames = 1

    def __init__(self):
        super().__init__()
        self.frame_feedback = {}
        self.msgs = []

    def send(self, msg):
        self.msgs.append(msg)


def test_framesender_1_1():

    fs = MyFrameSender()
    fs.max_buffered_frames = 1
    fs.max_queued_frames = 1

    im = np.array([[1, 2], [3, 4]], np.uint8)

    assert len(fs.msgs) == 0

    # Send a frame
    fs.send_frame(im)
    assert len(fs.msgs) == 1
    assert len(fs._pending_frames) == 0

    # Send another, this one is queued
    fs.send_frame(im)
    assert len(fs.msgs) == 1
    assert len(fs._pending_frames) == 1

    # Queue is full, so this one is dropped
    fs.send_frame(im)
    assert len(fs.msgs) == 1
    assert len(fs._pending_frames) == 1

    assert fs.stats["received_frames"] == 3
    assert fs.stats["sent_frames"] == 1
    assert fs.stats["dropped_frames"] == 1
    assert fs.stats["confirmed_frames"] == 0

    # Flush
    fs.frame_feedback["index"] = 1
    fs.frame_feedback["timestamp"] = fs.msgs[-1]["timestamp"]
    fs.frame_feedback["localtime"] = time.time()
    fs._iter()

    assert len(fs.msgs) == 2
    assert len(fs._pending_frames) == 0

    # Now we can send another
    fs.send_frame(im)
    assert len(fs.msgs) == 2
    assert len(fs._pending_frames) == 1

    assert fs.stats["received_frames"] == 4
    assert fs.stats["sent_frames"] == 2
    assert fs.stats["dropped_frames"] == 1
    assert fs.stats["confirmed_frames"] == 1


def test_framesender_2_3():

    fs = MyFrameSender()
    fs.max_buffered_frames = 2
    fs.max_queued_frames = 3

    im = np.array([[1, 2], [3, 4]], np.uint8)

    assert len(fs.msgs) == 0

    # 1 Send a frame
    fs.send_frame(im)
    assert len(fs.msgs) == 1
    assert len(fs._pending_frames) == 0

    # 2 Send a frame
    fs.send_frame(im)
    assert len(fs.msgs) == 2
    assert len(fs._pending_frames) == 0

    # 1 Send another, this one is queued
    fs.send_frame(im)
    assert len(fs.msgs) == 2
    assert len(fs._pending_frames) == 1

    # 2 Send another, this one is queued
    fs.send_frame(im)
    assert len(fs.msgs) == 2
    assert len(fs._pending_frames) == 2

    # 3 Send another, this one is queued
    fs.send_frame(im)
    assert len(fs.msgs) == 2
    assert len(fs._pending_frames) == 3

    # Queue is full, so this one is dropped
    fs.send_frame(im)
    assert len(fs.msgs) == 2
    assert len(fs._pending_frames) == 3

    assert fs.stats["received_frames"] == 6
    assert fs.stats["sent_frames"] == 2
    assert fs.stats["dropped_frames"] == 1
    assert fs.stats["confirmed_frames"] == 0

    # Flush
    fs.frame_feedback["index"] = 2
    fs.frame_feedback["timestamp"] = fs.msgs[-1]["timestamp"]
    fs.frame_feedback["localtime"] = time.time()
    fs._iter()

    assert len(fs.msgs) == 4
    assert len(fs._pending_frames) == 1

    # Now we can send another
    fs.send_frame(im)
    assert len(fs.msgs) == 4
    assert len(fs._pending_frames) == 2

    assert fs.stats["received_frames"] == 7
    assert fs.stats["sent_frames"] == 4
    assert fs.stats["dropped_frames"] == 1
    assert fs.stats["confirmed_frames"] == 2


if __name__ == "__main__":
    test_framesender_1_1()
    test_framesender_2_3()
