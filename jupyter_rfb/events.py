"""
Events passed to ``RemoteFrameBuffer.handle_event()`` are dict objects.
Each dict has a key `event_type`, as well as additional keys to provide
information regarding the event. The possible event types are:

* **resize**: emitted when the widget changes size.
  This event is throttled.

    * *width*: in logical pixels.
    * *height*: in logical pixels.
    * *pixel_ratio*: the pixel ratio between logical and physical pixels.

* **close**: emitted when the widget is closed (i.e. destroyed).
  This event has no additional keys.

* **pointer_down**: emitted when the user interacts with mouse,
  touch or other pointer devices, by pressing it down.

    * *x*: horizontal position of the pointer within the widget.
    * *y*: vertical position of the pointer within the widget.
    * *button*: the button to which this event applies.
      With 0 no button, 1 left, 2 right, 3 middle, etc.
    * *buttons*: a list of buttons being pressed down.
    * *modifiers*: a list of modifier keys being pressed down,
      e.g. "Shift" or "Control".
    * *ntouches*: the number of simultaneous pointers being down.
    * *touches*: a dict with int id's and dict values that have keys
      "x", "y", "pressure".

* **pointer_up**: emitted when the user releases a pointer.
  This event has the same keys as the pointer down event.

* **pointer_move**: emitted when the user moves a pointer.
  This event has the same keys as the pointer down event.
  This event is throttled.

* **double_click**: emitted on a double-click.
  This event looks like a pointer event, but without the touches.

* **wheel**: emitted when the mouse-wheel is used (scrolling).

    * *dx*: the horizontal scroll delta.
    * *dy*: the vertcal scroll delta.
    * *x*: the mouse horizontal position during the scroll.
    * *y*: the mouse vertical position during the scroll.
    * *modifiers*: a list of modifier keys being pressed down.

* **key_down**: emitted when a key is pressed down.

    * *key*: the (string) key being pressed, e.g. "a", "5", "%" or "Escape".
    * *modifiers*: a list of modifier keys being pressed down.

* **key_up**: emitted when a key is released.
  This event has the same keys as the key down event.

"""

# flake8: noqa
# The only purpose of this module is to document the events.
# In Sphinx autodoc we can use automodule.
# In Pyzo/Spyder/Jupyter a user can do ``jupyter_rfb.events?``.
