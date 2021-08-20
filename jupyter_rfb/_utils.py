import io
import builtins
import traceback
from base64 import encodebytes

import ipywidgets

from ._png import array2png

_original_print = builtins.print


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


class Snapshot:
    """An object representing an image snapshot from a RemoteFrameBuffer.

    Use this object as a cell output to show the image in the output.
    """

    def __init__(self, array, width, height, title="snapshot", class_name=None):
        self._array = array
        self._width = width
        self._height = height
        self._title = title
        self._class_name = class_name

    def _repr_mimebundle_(self, **kwargs):
        return {"text/html": self._get_html()}

    def get_array(self):
        """Return the snapshot as a numpy array."""
        return self._array

    def save(self, file):
        """Save the snapshot to a file-object or filename, in PNG format."""
        png_data = array2png(self._array)
        if hasattr(file, "write"):
            file.write(png_data)
        else:
            with open(file, "wb") as f:
                f.write(png_data)

    def _get_html(self, id=None):
        if self._array is None:
            return ""
        # Convert to PNG
        png_data = array2png(self._array)
        preamble = "data:image/png;base64"
        src = preamble + encodebytes(png_data).decode()
        # Create html repr
        class_str = f"class='{self._class_name}'" if self._class_name else ""
        img_style = f"width:{self._width}px;height:{self._height}px;"
        tt_style = "position: absolute; top:0; left:0; padding:1px 3px; "
        tt_style += (
            "background: #777; color:#fff; font-size: 90%; font-family:sans-serif; "
        )
        html = f"""
            <div {class_str} style='position:relative;'>
                <img src='{src}' style='{img_style}' />
                <div style='{tt_style}'>{self._title}</div>
            </div>
            """
        return html.replace("\n", "").replace("    ", "").strip()
