Event spec
----------

The events in jupyter_rfb have standardized fields and behavior:

https://pygfx.org/renderview/

.. note::

    Previously, jupyter_rfb defined its own event spec, known as the 'jupyter_rfb
    event spec'. This spec was adopted by other projects, most notably wgpu-py and
    `rendercanvas <https://github.com/pygfx/rendercanvas>`_. To make it easier to
    share the JS implementation, and adopt the spec in other projects, it was
    renamed to the 'renderview spec' and got it's own home at a dedicated `repo <https://github.com/pygfx/renderview>`_.
