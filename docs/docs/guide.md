# The jupyter_rfb guide


## Installation

To install use pip:
```bash
$ pip install -U jupyter_rfb
```

(Developers, see the [readme](https://github.com/vispy/jupyter_rfb) for a dev installation.)


## Subclassing the widget

The provided `RemoteFrameBuffer` class cannot do much by itself, but it serves as
a basis for widgets that want to generate images at the server, and be informed
of user events. The way to use `jupyter_rfb` is therefore to create a subclass
and implement two methods.

The first method to implement is `get_frame()`, which should return an (uint8) numpy array:
```py
class MyRemoteFrameBuffer(jupyter_rfb.RemoteFrameBuffer):

    def get_frame(self):
        return np.random.uniform(0, 255, (100,100)).astype(np.uint8)

```

The second method to implement is `handle_event()`:
```py
class MyRemoteFrameBuffer(jupyter_rfb.RemoteFrameBuffer):

    def get_frame(self):
        ...

    def handle_event(self, event):
        event_type = event["event_type"]
        if event_type == "resize":
            self.logical_size = event["width"], event["height"]
            self.pixel_ratio = event["pixel_ratio"]
        elif event_type == "pointer_down":
            ...
```

This is where you can react to changes and user interactions. The most
important one may be the resize event, so that you can match the array
size to the occupied pixels on screen.


## Scheduling draws

The `get_frame()` method is called automatically when a new draw is
performed. There are cases when the widget knows that a redraw is
(probably) required, such as when the widget is resized.

If you want to trigger a redraw (e.g. because certain state has
changed in reaction to user interaction), you can call
`widget.request_draw()` to schedule a new draw.

The widget will only perform a new draw when it is ready to do so. To
be more precise, the client must have confirmed receiving the nth latest frame.
This mechanism makes that draws in Python match the speed by which
the frames can be communicated and displayed. This is also known as
throttling and helps realize minimal lag and high FPS.


## Event throttling

Events go from the client (browser) to the server (Python). Some of
these are throttled so they are emitted a maximum number of times per
second. This is to avoid spamming the io and server process. The
throttling applies to the resize, scroll, and pointer_move events.


## Measuring statistics

The `RemoteFrameBuffer` class has a property `stats` that returns a dict
with performance metrics:
```py
>>> w.reset_stats()  # start measuring
    ... interact or run a test
>>> w.stats
{
    ...
}
```


## Performance tips

The framerate that can be obtained depends on a number of factors:

* The size of a frame: larger frames generally take longer to encode.
* The entropy (information density) of a frame: random data takes longer to compress.
* How many widgets are drawing simultaneously (they use the same communication channel).
* How much other work your CPU does (image compression is CPU-bound).
