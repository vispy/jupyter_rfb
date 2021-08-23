import io
import builtins
import traceback
from base64 import encodebytes

from IPython.display import DisplayObject
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


class Snapshot(DisplayObject):
    """An IPython DisplayObject representing an image snapshot.

    The ``data`` attribute is the image array object. One could use
    this to process the data further, e.g. storing it to disk.
    """

    # Not an IPython.display.Image, because we want to use some HTML to
    # give it a custom css class and a title.

    def __init__(self, data, width, height, title="snapshot", class_name=None):
        super().__init__(data)
        self.width = width
        self.height = height
        self.title = title
        self.class_name = class_name

    def _check_data(self):
        assert hasattr(self.data, "shape") and hasattr(self.data, "dtype")

    def _repr_mimebundle_(self, **kwargs):
        return {"text/html": self._repr_html_()}

    def _repr_html_(self):
        # Convert to PNG
        png_data = array2png(self.data)
        preamble = "data:image/png;base64,"
        src = preamble + encodebytes(png_data).decode()
        # Create html repr
        class_str = f"class='{self.class_name}'" if self.class_name else ""
        img_style = f"width:{self.width}px;height:{self.height}px;"
        tt_style = "position: absolute; top:0; left:0; padding:1px 3px; "
        tt_style += (
            "background: #777; color:#fff; font-size: 90%; font-family:sans-serif; "
        )
        html = f"""
            <div {class_str} style='position:relative;'>
                <img src='{src}' style='{img_style}' />
                <div style='{tt_style}'>{self.title}</div>
            </div>
            """
        return html.replace("\n", "").replace("    ", "").strip()
