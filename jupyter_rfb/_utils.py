import io
import builtins
import traceback

import ipywidgets

from ._png import array2png
from ._jpg import array2jpg


_original_print = builtins.print


def array2compressed(array, quality=90):
    """Convert the given image (a numpy array) as a compressed array.

    If the quality is 100, a PNG is returned. Otherwise, JPEG is
    preferred and PNG is used as a fallback. Returns (mimetype, bytes).
    """

    # Drop alpha channel if there is one
    if len(array.shape) == 3 and array.shape[2] == 4:
        array = array[:, :, :3]

    if quality >= 100:
        mimetype = "image/png"
        result = array2png(array)
    else:
        mimetype = "image/jpeg"
        result = array2jpg(array, quality)
        if result is None:
            mimetype = "image/png"
            result = array2png(array)

    return mimetype, result


class RFBOutputContext(ipywidgets.Output):
    """An output widget with a different implementation of the context manager.

    Handles prints and errors in a more reliable way, that is also
    lightweight (i.e. no peformance cost).

    See https://github.com/vispy/jupyter_rfb/issues/35
    """

    capture_print = False
    _prev_print = None

    def print(self, *args, **kwargs):
        """Print function that show up in the output."""
        f = io.StringIO()
        kwargs.pop("file", None)
        _original_print(*args, file=f, flush=True, **kwargs)
        text = f.getvalue()
        self.append_stdout(text)

    def __enter__(self):
        """Enter context, replace print function."""
        if self.capture_print:
            self._prev_print = builtins.print
            builtins.print = self.print
        return self

    def __exit__(self, etype, value, tb):
        """Exit context, restore print function and show any errors."""
        if self.capture_print and self._prev_print is not None:
            builtins.print = self._prev_print
            self._prev_print = None
        if etype:
            err = "".join(traceback.format_exception(etype, value, tb))
            self.append_stderr(err)
            return True  # declare that we handled the exception
