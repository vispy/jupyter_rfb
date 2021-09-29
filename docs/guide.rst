The jupyter_rfb guide
=====================

Installation
------------

Install with pip:

.. code-block::

    pip install -U jupyter_rfb

Or to install into a conda environment:

.. code-block::

    conda install -c conda-forge jupyter-rfb

For better performance, also install ``simplejpeg`` or ``pillow``.

If you plan to hack on this library, see the :doc:`contributor guide <contributing>`
for a dev installation and more.


Subclassing the widget
----------------------

The provided :class:`RemoteFrameBuffer <jupyter_rfb.RemoteFrameBuffer>` class cannot do much by itself, but it provides
a basis for widgets that want to generate images at the server, and be informed
of user events. The way to use ``jupyter_rfb`` is therefore to create a subclass
and implement two specific methods.

The first method to implement is :func:`.get_frame() <jupyter_rfb.RemoteFrameBuffer.get_frame>`, which should return a uint8 numpy array. For example:

.. code-block:: py

    class MyRemoteFrameBuffer(jupyter_rfb.RemoteFrameBuffer):

        def get_frame(self):
            return np.random.uniform(0, 255, (100,100)).astype(np.uint8)

The second method to implement is :func:`.handle_event() <jupyter_rfb.RemoteFrameBuffer.handle_event>`,
which accepts an event object. This is where you can react to changes
and user interactions. The most important one may be the resize event,
so that you can match the array size to the region on screen. For
example:

.. code-block:: py

    class MyRemoteFrameBuffer(jupyter_rfb.RemoteFrameBuffer):

        def handle_event(self, event):
            event_type = event["event_type"]
            if event_type == "resize":
                self.logical_size = event["width"], event["height"]
                self.pixel_ratio = event["pixel_ratio"]
            elif event_type == "pointer_down":
                pass  # ...


Logical vs physical pixels
--------------------------

The size of e.g. the resize event is expressed in logical pixels. This
is a unit of measurement that changes as the user changes the browser
zoom level.

By multiplying the logical size with the pixel-ratio, you obtain the
physical size, which represents the actual pixels of the screen. With
a zoom level of 100% the pixel-ratio is 1 on a regular display and 2
on a HiDPI display, although the actual values may also be affected by
the OS's zoom level.


Scheduling draws
----------------

The :func:`.get_frame() <jupyter_rfb.RemoteFrameBuffer.get_frame>`
method is called automatically when a new draw is
performed. There are cases when the widget knows that a redraw is
(probably) required, such as when the widget is resized.

If you want to trigger a redraw (e.g. because certain state has
changed in reaction to user interaction), you can call
:func:`.request_draw() <jupyter_rfb.RemoteFrameBuffer.request_draw>` to schedule a new draw.

The scheduling of draws is done in such a way to avoid images being
produced faster than the client can consume them - a process known as
throttling. In more detail: the client sends a confirmation for each
frame that it receives, and the server waits with producing a new frame
until the client has confirmed receiving the nth latest frame. This
mechanism causes the calls to :func:`.get_frame() <jupyter_rfb.RemoteFrameBuffer.get_frame>`
to match the speed by which
the frames can be communicated and displayed. This helps minimize the
lag and optimize the FPS.


Event throttling
----------------

Events go from the client (browser) to the server (Python). Some of
these are throttled so they are emitted a maximum number of times per
second. This is to avoid spamming the communication channel and server
process. The throttling applies to the resize, scroll, and pointer_move
events.


Taking snapshots
----------------

In a notebook, the :meth:`.snapshot() <jupyter_rfb.RemoteFrameBuffer.snapshot>`
method can be used to create a picture of the current state of the
widget. This image remains visible when the notebook is in off-line
mode (e.g. in nbviewer). This functionality can be convenient if you're
using a notebook to tell a story, and you want to display a certain
result that is still visible in off-line mode.

When a widget is first displayed, it automatically creates a
snapshot, which is hidden by default, but becomes visible when the
widget itself is not loaded. In other words, example notebooks
have pretty pictures!


Exceptions and logging
----------------------

The :func:`.handle_event() <jupyter_rfb.RemoteFrameBuffer.handle_event>`
and :func:`.get_frame() <jupyter_rfb.RemoteFrameBuffer.get_frame>`
methods are called from a Jupyter
COM event and in an asyncio task, respectively. Under these circumstances,
Jupyter Lab/Notebook may swallow exceptions as well as writes to stdout/stderr.
See `issue #35 <https://github.com/vispy/jupyter_rfb/issues/35>`_ for details.
These are limitation of Jupyter, and we should expect these to be fixed/improved in the future.

In jupyter_rfb we take measures to make exceptions raised in
either of these methods result in a traceback shown right above the
widget. To ensure that calls to ``print()`` in these methods are also
shown, use ``self.print()`` instead.

Note that any other streaming to stdout and stderr (e.g. logging) may
not become visible anywhere.


Measuring statistics
--------------------

The :class:`RemoteFrameBuffer <jupyter_rfb.RemoteFrameBuffer>` class has a
method :func:`.get_stats() <jupyter_rfb.RemoteFrameBuffer.get_stats>` that
returns a dict with performance metrics:

.. code-block:: py

    >>> w.reset_stats()  # start measuring
        ... interact or run a test
    >>> w.get_stats()
    {
        ...
    }


Performance tips
----------------

The framerate that can be obtained depends on a number of factors:

* The size of a frame: smaller frames generally encode faster and result
  in smaller blobs, causing less strain on both CPU and IO.
* How many widgets are drawing simultaneously: they use the same communication channel.
* The ``widget.quality`` trait: lower quality results in faster encoding and smaller blobs.
* When using lossless images (``widget.quality == 100``), the entropy
  (information density) of a frame also matters, because for PNG, high entropy
  data takes longer to compress and results in larger blobs.

For more details about performance considerations in the implementation of ``jupyter_rfb``,
see `issue #3 <https://github.com/vispy/jupyter_rfb/issues/3>`_.
