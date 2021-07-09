import time
from base64 import encodebytes

import ipywidgets as widgets
from traitlets import Unicode, Int, Float, Bool
import tornado

from ._png import array2png


# See js/lib/example.js for the frontend counterpart to this file.


# todo: ...
# - test speed of pillow vs current approach
# - test speed of jpg (via pillow)
# - look into rate limiting strategies like diff pngs


class FrameSenderMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._received_frames = 0
        self._send_frames = 0
        self._pending_frames = []

        self._timer = tornado.ioloop.PeriodicCallback(self._iter, 20, 0.05)
        self._timer.start()

    def push_frame(self, array):
        self._received_frames += 1
        self._pending_frames.append(array)
        self._iter()

    def _iter(self, *args):
        if self._pending_frames:
            if self.last_index >= self._send_frames:
                if self.last_timestamp + 0.5 < time.time():
                    self._send_frame(self._pending_frames.pop(0))

    def _send_frame(self, array):
            timestamp = time.time()
            self._send_frames += 1

            # Turn array into a based64-encoded PNG
            png_data = array2png(array)
            preamble = "data:image/png;base64,"
            src = preamble + encodebytes(png_data).decode()

            # Compose message and send
            msg = dict(
                type="framebufferdata",
                src=src,
                index=self._send_frames,
                timestamp=timestamp,
            )
            self.send(msg)


@widgets.register
class RemoteFrameBuffer(widgets.DOMWidget, FrameSenderMixin):
    """Widget that shows a remote frame buffer."""

    # Name of the widget view class in front-end
    _view_name = Unicode('RemoteFrameBufferView').tag(sync=True)

    # Name of the widget model class in front-end
    _model_name = Unicode('RemoteFrameBufferModel').tag(sync=True)

    # Name of the front-end module containing widget view
    _view_module = Unicode('jupyter_rfb').tag(sync=True)

    # Name of the front-end module containing widget model
    _model_module = Unicode('jupyter_rfb').tag(sync=True)

    # Version of the front-end module containing widget view
    _view_module_version = Unicode('^0.1.0').tag(sync=True)
    # Version of the front-end module containing widget model
    _model_module_version = Unicode('^0.1.0').tag(sync=True)

    # Widget specific properties
    last_index = Int(0).tag(sync=True)
    last_timestamp = Float(time.time()).tag(sync=True)

    css_width = Unicode("100%").tag(sync=True)
    css_height = Unicode("300px").tag(sync=True)
    resizable = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_msg(self._receive_events)

    def _receive_events(self, widget, content, buffers):
        print(content)
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

