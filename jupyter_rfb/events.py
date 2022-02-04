"""
This spec specifies the events that are passed to the widget's
:func:`.handle_event() <jupyter_rfb.RemoteFrameBuffer.handle_event>` method.
Events are simple dict objects containing at least the key `event_type`.
Additional keys provide more information regarding the event.


Event types
-----------

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
    * *button*: the button to which this event applies. See section below for details.
    * *buttons*: a list of buttons being pressed down.
    * *modifiers*: a list of modifier keys being pressed down. See section below for details.
    * *ntouches*: the number of simultaneous pointers being down.
    * *touches*: a dict with int keys and dict values.
      The values contain "x", "y", "pressure".

* **pointer_up**: emitted when the user releases a pointer.
  This event has the same keys as the pointer down event.

* **pointer_move**: emitted when the user moves a pointer.
  This event has the same keys as the pointer down event.
  This event is throttled.

* **double_click**: emitted on a double-click.
  This event looks like a pointer event, but without the touches.

* **wheel**: emitted when the mouse-wheel is used (scrolling),
  or when scrolling/pinching on the touchpad/touchscreen.

  Similar to the JS wheel event, the values of the deltas depend on the
  platform and whether the mouse-wheel, trackpad or a touch-gesture is
  used. Also, scrolling can be linear or have inertia. As a rule of
  thumb, one "wheel action" results in a cumulative ``dy`` of around
  100. Positive values of ``dy`` are associated with scrolling down and
  zooming out. Positive values of ``dx`` are associated with scrolling
  to the right. (A note for Qt users: the sign of the deltas is (usually)
  reversed compared to the QWheelEvent.)

  On MacOS, using the mouse-wheel while holding shift results in horizontal
  scrolling. In applications where the scroll dimension does not matter,
  it is therefore recommended to use `delta = event['dy'] or event['dx']`.

    * *dx*: the horizontal scroll delta (positive means scroll right).
    * *dy*: the vertical scroll delta (positive means scroll down or zoom out).
    * *x*: the mouse horizontal position during the scroll.
    * *y*: the mouse vertical position during the scroll.
    * *modifiers*: a list of modifier keys being pressed down.

* **key_down**: emitted when a key is pressed down.

    * *key*: the key being pressed as a string. See section below for details.
    * *modifiers*: a list of modifier keys being pressed down.

* **key_up**: emitted when a key is released.
  This event has the same keys as the key down event.


Mouse buttons
-------------

* 0: No button.
* 1: Left button.
* 2: Right button.
* 3: Middle button
* 4-9: etc.


Keys
----

The key names follow the `browser spec <https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent>`_.

* Keys that represent a character are simply denoted as such. For these the case matters:
  "a", "A", "z", "Z" "3", "7", "&", " " (space), etc.
* The modifier keys are:
  "Shift", "Control", "Alt", "Meta".
* Some example keys that do not represent a character:
  "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "F1", "Backspace", etc.


Coordinate frame
----------------

The coordinate frame is defined with the origin in the top-left corner.
Positive `x` moves to the right, positive `y` moves down.


Event capturing
---------------

Since jupyter_rfb represents a widget in the browser, some events only
work when it has focus  (having received a pointer down). This applies
to the *key_down*, *key_up*, and *wheel* events.


Event throttling
----------------

To avoid straining the IO, certain events can be throttled. Their effect
is accumulated if this makes sense (e.g. wheel event). The consumer of
the events should take this into account. The events that are throttled
in jupyte_rfb widgets are *resize*, *pointer_move* and *wheel*.

"""

# flake8: noqa
# The only purpose of this module is to document the events.
# In Sphinx autodoc we can use automodule.
# In Pyzo/Spyder/Jupyter a user can do ``jupyter_rfb.events?``.
