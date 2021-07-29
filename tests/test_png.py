"""Test png module."""

import os
import tempfile

import numpy as np
from pytest import raises

from jupyter_rfb._png import array2png

tempdir = tempfile.gettempdir()

shape0 = 100, 100
im0 = b"\x77" * 10000

shape1 = 5, 5
im1 = b""
im1 += b"\x00\x00\x99\x00\x00"
im1 += b"\x00\x00\xff\x00\x00"
im1 += b"\x99\xff\xff\xff\x99"
im1 += b"\x00\x00\xff\x00\x00"
im1 += b"\x00\x00\x99\x00\x00"

shape2 = 6, 6
im2 = b""
im2 += b"\x00\x00\x00\x88\x88\x88"
im2 += b"\x00\x00\x00\x88\x88\x88"
im2 += b"\x00\x00\x00\x88\x88\x88"
im2 += b"\x44\x44\x44\xbb\xbb\xbb"
im2 += b"\x44\x44\x44\xbb\xbb\xbb"
im2 += b"\x44\x44\x44\xbb\xbb\xbb"

shape3 = 5, 5, 3
im3 = bytearray(5 * 5 * 3)
im3[0::3] = im0[:25]
im3[1::3] = im1[:25]
im3[2::3] = im2[:25]

shape4 = 5, 5, 4
im4 = bytearray(5 * 5 * 4)
im4[0::4] = im0[:25]
im4[1::4] = im1[:25]
im4[2::4] = im2[:25]
im4[3::4] = im0[:25]

im0 = np.frombuffer(im0, np.uint8).reshape(shape0)
im1 = np.frombuffer(im1, np.uint8).reshape(shape1)
im2 = np.frombuffer(im2, np.uint8).reshape(shape2)
im3 = np.frombuffer(im3, np.uint8).reshape(shape3)
im4 = np.frombuffer(im4, np.uint8).reshape(shape4)

ims = im0, im1, im2, im3, im4
shapes = shape0, shape1, shape2, shape3, shape4


def test_writing():
    """Test writing png."""

    # Get bytes
    b0 = array2png(im0)
    b1 = array2png(im1)
    b2 = array2png(im2)
    b3 = array2png(im3)
    b4 = array2png(im4)

    blobs = b0, b1, b2, b3, b4

    # Write to disk (also for visual inspection)
    for i in range(5):
        filename = os.path.join(tempdir, "test%i.png" % i)
        with open(filename, "wb") as f:
            f.write(blobs[i])
    print("wrote PNG test images to", tempdir)

    assert len(b1) < len(b4)  # because all zeros are easier to compress

    # Check that providing file object yields same result
    with open(filename + ".check", "wb") as f:
        array2png(im4, f)
    bb1 = open(filename, "rb").read()
    bb2 = open(filename + ".check", "rb").read()
    assert len(bb1) == len(bb2)
    assert bb1 == bb2

    # Test shape with singleton dim
    b1_check = array2png(im1.reshape(shape1[0], shape1[1], 1))
    assert b1_check == b1


def test_writing_failures():
    """Test that errors are raised when needed."""

    with raises(ValueError):
        array2png([1, 2, 3, 4])

    with raises(ValueError):
        array2png(b"x" * 10)

    with raises(ValueError):
        array2png(im0.reshape(-1))

    with raises(ValueError):
        array2png(im4.reshape(-1, -1, 8))
