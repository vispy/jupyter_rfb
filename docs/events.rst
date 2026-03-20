Event spec
==========

The events in jupyter_rfb have standardized fields and behavior:

https://pygfx.org/renderview/


.. note::

    Previously, jupyter_rfb defined its own event spec, known as the 'jupyter_rfb
    event spec'. This spec was adopted by other projects, most notably wgpu-py and
    `rendercanvas <https://github.com/pygfx/rendercanvas>`_. To make it easier to
    share the JS implementation, and adopt the spec in other projects, it was
    renamed to the 'renderview spec' and got it's own home at a dedicated `repo <https://github.com/pygfx/renderview>`_.


Backwards compatibility
-----------------------

For the time being, the events objects also include the old fields, for backwards compatibility:

* ``event_type`` (now ``type``)
* ``time_stamp``  (now ``timestamp``)
* ``pixel_ratio``  (now ``ratio``)

This behavior can be changed in subclasses with the ``_event_compatibility`` bitmask:

* Set ``_event_compatibility = 1`` to get only the old fields.
* Set ``_event_compatibility = 2`` to get only the new fields.
* Set ``_event_compatibility = 3`` to get both old and new fields.

Currently, the default is 3. When both Vispy and rendercanvas (and possible
other downstream projects) have adapted to the new API for a sufficiently long
time, the compatibility mode will be removed.
