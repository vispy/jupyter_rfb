The jupyter_rfb guide
=====================

Installation
------------

To install use pip:

.. code-block::

    pip install -U jupyter_rfb

Developers, see the `readme <https://github.com/vispy/jupyter_rfb>`_ for a dev installation.


Subclassing the widget
----------------------

The provided :class:`RemoteFrameBuffer <jupyter_rfb.RemoteFrameBuffer>` class cannot do much by itself, but it serves as
a basis for widgets that want to generate images at the server, and be informed
of user events. The way to use ``jupyter_rfb`` is therefore to create a subclass
and implement two methods.

The first method to implement is ``get_frame()``, which should return an (uint8) numpy array:

.. code-block:: py

    class MyRemoteFrameBuffer(jupyter_rfb.RemoteFrameBuffer):

        def get_frame(self):
            return np.random.uniform(0, 255, (100,100)).astype(np.uint8)


The second method to implement is ``handle_event()``:

.. code-block:: py

    class MyRemoteFrameBuffer(jupyter_rfb.RemoteFrameBuffer):

        def get_frame(self):
            pass  # ...

        def handle_event(self, event):
            event_type = event["event_type"]
            if event_type == "resize":
                self.logical_size = event["width"], event["height"]
                self.pixel_ratio = event["pixel_ratio"]
            elif event_type == "pointer_down":
                pass  # ...

This is where you can react to changes and user interactions. The most
important one may be the resize event, so that you can match the array
size to the occupied pixels on screen.


Scheduling draws
----------------

The ``get_frame()`` method is called automatically when a new draw is
performed. There are cases when the widget knows that a redraw is
(probably) required, such as when the widget is resized.

If you want to trigger a redraw (e.g. because certain state has
changed in reaction to user interaction), you can call
``widget.request_draw()`` to schedule a new draw.

The widget will only perform a new draw when it is ready to do so. To
be more precise, the client must have confirmed receiving the nth latest frame.
This mechanism makes that draws in Python match the speed by which
the frames can be communicated and displayed. This is also known as
throttling and helps realize minimal lag and high FPS.


Event throttling
----------------

Events go from the client (browser) to the server (Python). Some of
these are throttled so they are emitted a maximum number of times per
second. This is to avoid spamming the io and server process. The
throttling applies to the resize, scroll, and pointer_move events.


Exceptions and logging
----------------------

The ``handle_event()`` and ``get_frame()`` methods are called from a COM event
and in an asyncio task, respectively. Under these circumstances,
Jupyter Lab/Notebook may swallow exceptions and writes to stdout/stderr.
See `issue #35 <https://github.com/vispy/jupyter_rfb/issues/35>`_ for details.

In jupyter_rfb we take measures such that exceptions raised in
either of these methods result in a traceback shown right above the
widget. To ensure that calls to ``print()`` in these methods are also
shown, use ``self.print()`` instead.

Note that any other streaming to stdout and stderr (e.g. logging) may
not become visible anywhere.


Measuring statistics
--------------------

The ``RemoteFrameBuffer`` class has a method ``get_stats()`` that
returns a dict with performance metrics:

.. code-block::

    >>> w.reset_stats()  # start measuring
        ... interact or run a test
    >>> w.get_stats()
    {
        ...
    }


Performance tips
----------------

The framerate that can be obtained depends on a number of factors:

* The size of a frame: larger frames generally take longer to encode.
* The entropy (information density) of a frame: random data takes longer to compress.
* How many widgets are drawing simultaneously (they use the same communication channel).
* How much other work your CPU does (image compression is CPU-bound).
