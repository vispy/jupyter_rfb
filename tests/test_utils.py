"""Test the things in the utils module."""

import pytest
import numpy as np
from jupyter_rfb._utils import array2compressed, Snapshot
from jupyter_rfb import _jpg


def test_array2compressed():
    """Test the array2compressed function."""

    pytest.importorskip("simplejpeg")

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
