"""Test the things in the utils module."""

import numpy as np
from jupyter_rfb._utils import array2compressed, RFBOutputContext, Snapshot
from jupyter_rfb import _jpg


def test_array2compressed():
    """Test the array2compressed function."""

    # This test assumes that a JPEG encoder is available

    im = np.random.randint(0, 255, (100, 100, 3)).astype(np.uint8)

    # Basic check
    preamble, bb = array2compressed(im)
    assert isinstance(preamble, str)
    assert isinstance(bb, bytes)
    assert "jpeg" in preamble and "png" not in preamble

    # Check compression
    preamble1, bb1 = array2compressed(im, 90)
    preamble2, bb2 = array2compressed(im, 30)
    assert len(bb2) < len(bb1)

    # Check quality 100
    preamble3, bb3 = array2compressed(im, 100)
    assert len(bb3) > len(bb1)

    assert "jpeg" in preamble1 and "png" not in preamble1
    assert "jpeg" in preamble2 and "png" not in preamble1
    assert "png" in preamble3 and "jpeg" not in preamble3

    # Check that RGBA is made RGB
    im4 = np.random.randint(0, 255, (100, 100, 4)).astype(np.uint8)
    im3 = im4[:, :, :3]
    _, bb1 = array2compressed(im4, 90)
    _, bb2 = array2compressed(im3, 90)
    assert bb1 == bb2

    # Also for PNG mode
    _, bb1 = array2compressed(im4, 100)
    _, bb2 = array2compressed(im3, 100)
    assert bb1 == bb2

    # Check fallback - disable JPEG encoding, we get PNG
    _jpg.encoder = _jpg.StubJpegEncoder()
    try:

        preamble, bb = array2compressed(im)
        assert isinstance(preamble, str)
        assert isinstance(bb, bytes)
        assert "png" in preamble and "jpeg" not in preamble

    finally:
        _jpg.encoder = _jpg.select_encoder()

    # Should be back to normal now
    preamble, bb = array2compressed(im)
    assert "jpeg" in preamble and "png" not in preamble


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
    assert s.data is a

    # Most importantly, it has a Jupyter mime data!
    data = s._repr_mimebundle_()
    assert "text/html" in data
    html = data["text/html"]
    assert "data:image/png;base64" in html  # looks like the png is in there
    assert "width:5px" in html and "height:5px" in html  # logical size
    assert "class='KLS'" in html  # css class name
    assert "footitle" in html  # the title
