# jupyter_rfb guide


## Installation

To install use pip:
```bash
$ pip install jupyter_rfb
```

(Developers, see the [readme](https://github.com/vispy/jupyter_rfb) for a dev installation.)


## Subclassing the widget

The widget provided by `jupyter_rfb` cannot do much by itself, but it provides
a basis for other tools that want to generate frames at the server and be informed
of client-side events. The way to use `jupyter_rfb` is therefore to create a subclass
and implement two methods.

The first method to implement is `on_draw()`:
```py
class MyRemoteFrameBuffer(jupyter_rfb.RemoteFrameBuffer):

    def on_draw(self):
        TODO

```

In this method you let the server generate an image for display. It is called
automatically when the widget is ready to send another frame.

Actually, this is not yet how it works, we now have `send_frame()`. TODO - fix docs

The second method to implement is `on_event()`:
```py
class MyRemoteFrameBuffer(jupyter_rfb.RemoteFrameBuffer):

    def on_draw(self):
        ...

    def on_event(self, event):
        event_type = event["event_type"]
        if event_type == "resize":
            self.logical_size = event["width"], event["height"]
            self.pixel_ratio = event["pixel_ratio"]
        elif event_type == "pointer_down":
            ...
```

This is where you can react to changes and interactions at the client side.


## Throttling


## Performance tips

The framerate that can be obtained depends on a number of factors:

* the size of a frame (larger frames generally take longer to encode).
* the entropy (information density) of frame (rando data is harder to compress).
* ...
