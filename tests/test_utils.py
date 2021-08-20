"""Test the things in the utils module."""

import os
import io
import tempfile

import numpy as np
from jupyter_rfb._utils import RFBOutputContext, Snapshot


class StubRFBOutputContext(RFBOutputContext):
    """A helper class for these tests."""

    def __init__(self):
        super().__init__()
        self.stdouts = []
        self.stderrs = []

    def append_stdout(self, msg):
        """Overloaded method."""
        self.stdouts.append(msg)

    def append_stderr(self, msg):
        """Overloaded method."""
        self.stderrs.append(msg)


def test_output_context():
    """Test the RFBOutputContext class."""

    c = StubRFBOutputContext()

    # The context captures errors and sends tracebacks to its "stdout stream"
    with c:
        1 / 0
    assert len(c.stderrs) == 1
    assert "Traceback" in c.stderrs[0]
    assert "ZeroDivisionError" in c.stderrs[0]

    # By default it does not capture prints
    with c:
        print("aa")
    assert len(c.stdouts) == 0

    # But we can turn that on
    c.capture_print = True
    print("aa")
    with c:
        print("bb")
        print("cc")
    print("dd")
    c.capture_print = False
    with c:
        print("ee")
    assert len(c.stdouts) == 2
    assert c.stdouts[0] == "bb\n"
    assert c.stdouts[1] == "cc\n"

    # The print is a proper print
    c.print("foo", "bar", sep="-", end=".")
    assert c.stdouts[-1] == "foo-bar."


def test_snapshot():
    """Test the Snapshot class."""

    a = np.zeros((10, 10), np.uint8)

    s = Snapshot(a, 5, 5, "footitle", "KLS")

    # The get_array method returns the raw data
    assert s.get_array() is a

    # You can save the data to file object
    f = io.BytesIO()
    s.save(f)
    bb1 = f.getvalue()
    assert bb1.startswith(b"\x89PNG")

    # Or to a filename
    filename = os.path.join(tempfile.gettempdir(), "test.png")
    s.save(filename)
    with open(filename, "rb") as f:
        bb2 = f.read()
    assert bb1 == bb2

    # Most importantly, it has a Jupyter mime data!
    data = s._repr_mimebundle_()
    assert "text/html" in data
    html = data["text/html"]
    assert "data:image/png;base64" in html  # looks like the png is in there
    assert "width:5px" in html and "height:5px" in html  # logical size
    assert "class='KLS'" in html  # css class name
    assert "footitle" in html  # the title
