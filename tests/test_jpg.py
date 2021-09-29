"""Test jpg module."""

import numpy as np
from pytest import raises

from jupyter_rfb._jpg import (
    array2jpg,
    select_encoder,
    SimpleJpegEncoder,
    PillowJpegEncoder,
)


def get_random_im(*shape):
    """Get a random image."""
    return np.random.randint(0, 255, shape).astype(np.uint8)


def test_array2jpg():
    """Tests for array2jpg function."""

    im = get_random_im(100, 100, 3)
    bb1 = array2jpg(im)  # has default quality
    bb2 = array2jpg(im, 20)
    assert isinstance(bb1, bytes)
    assert len(bb2) < len(bb1)


def test_simplejpeg_jpeg_encoder():
    """Test the simplejpeg encoder."""
    encoder = SimpleJpegEncoder()
    _perform_checks(encoder)
    _perform_error_checks(encoder)


def test_pillow_jpeg_encoder():
    """Test the pillow encoder."""
    encoder = PillowJpegEncoder()
    _perform_checks(encoder)
    _perform_error_checks(encoder)


def _perform_checks(encoder):

    # RGB
    im = get_random_im(100, 100, 3)
    bb1 = encoder.encode(im, 90)
    bb2 = encoder.encode(im, 20)
    assert isinstance(bb1, bytes)
    assert len(bb2) < len(bb1)

    # RGB non-contiguous
    im = get_random_im(100, 100, 3)
    bb1 = encoder.encode(im[20:-20, 20:-20, :], 90)
    bb2 = encoder.encode(im[20:-20, 20:-20, :], 20)
    assert isinstance(bb1, bytes)
    assert len(bb2) < len(bb1)

    # Gray1
    im = get_random_im(100, 100)
    bb1 = encoder.encode(im, 90)
    bb2 = encoder.encode(im, 20)
    assert isinstance(bb1, bytes)
    assert len(bb2) < len(bb1)

    # Gray2
    im = get_random_im(100, 100, 1)
    bb1 = encoder.encode(im, 90)
    bb2 = encoder.encode(im, 20)
    assert isinstance(bb1, bytes)
    assert len(bb2) < len(bb1)

    # Gray non-contiguous
    im = get_random_im(100, 100)
    bb1 = encoder.encode(im[20:-20, 20:-20], 90)
    bb2 = encoder.encode(im[20:-20, 20:-20], 20)
    assert isinstance(bb1, bytes)
    assert len(bb2) < len(bb1)


def _perform_error_checks(encoder):

    # JUst to verify that this is ok
    encoder.encode(get_random_im(10, 10, 3), 90)

    with raises(ValueError):  # not a numpy array
        encoder.encode([1, 2, 3, 4], 90)

    with raises(ValueError):  # not a numpy array
        encoder.encode(b"1234", 90)

    with raises(ValueError):  # NxMx2?
        encoder.encode(get_random_im(10, 10, 2), 90)

    with raises(ValueError):  # NxMx4?
        encoder.encode(get_random_im(10, 10, 4), 90)

    with raises(ValueError):
        encoder.encode(get_random_im(10, 10, 3).astype(np.float32), 90)


def raise_importerror():
    """Raise an import error (flake forces me to write this docstring)."""
    raise ImportError()


def test_select_encoder():
    """Test the JPEG encoder selection mechanism."""

    encoder = select_encoder()
    assert isinstance(encoder, (SimpleJpegEncoder, PillowJpegEncoder))

    # Sabotage
    simple_init = SimpleJpegEncoder.__init__
    pillow_init = PillowJpegEncoder.__init__
    try:
        SimpleJpegEncoder.__init__ = lambda self: raise_importerror()
        PillowJpegEncoder.__init__ = lambda self: raise_importerror()

        encoder = select_encoder()
        assert not isinstance(encoder, (SimpleJpegEncoder, PillowJpegEncoder))

        # Without a valid encoder, we get the stub encoder
        result = encoder.encode(get_random_im(10, 10, 3), 90)
        assert result is None

    finally:
        SimpleJpegEncoder.__init__ = simple_init
        PillowJpegEncoder.__init__ = pillow_init
