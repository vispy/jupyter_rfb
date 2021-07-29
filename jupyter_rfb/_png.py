import io
import struct
import zlib

import numpy as np


def array2png(array, file=None):
    """Create a png image from a numpy array.

    The written image is in RGB or RGBA format, with 8 bit precision,
    zlib-compressed, without interlacing.

    The provided array's shape must be either NxM (grayscale), NxMx1 (grayscale),
    NxMx3 (RGB) or NxNx4 (RGBA).
    """

    # Check types
    if hasattr(array, "shape") and hasattr(array, "dtype"):
        if array.dtype != "uint8":
            raise TypeError("Image array to convert to PNG must be uint8")
        original_shape = shape = array.shape
    else:
        raise ValueError(
            f"Invalid type for array, need ndarray-like, got {type(array)}"
        )

    # Allow grayscale: convert to RGB
    if len(shape) == 2 or (len(shape) == 3 and shape[2] == 1):
        shape = shape[0], shape[1], 3
        array = array.reshape(shape[:2])
        array3 = np.empty(shape, np.uint8)
        array3[..., 0] = array
        array3[..., 1] = array
        array3[..., 2] = array
        array = array3
    elif not array.flags.c_contiguous:
        array = array.copy()

    # Check shape
    if not (len(shape) == 3 and shape[2] in (3, 4)):
        raise ValueError(f"Unexpected image shape: {original_shape}")

    # Get file object
    f = io.BytesIO() if file is None else file

    def add_chunk(data, name):
        name = name.encode("ASCII")
        crc = zlib.crc32(data, zlib.crc32(name))
        f.write(struct.pack(">I", len(data)))
        f.write(name)
        f.write(data)
        f.write(struct.pack(">I", crc & 0xFFFFFFFF))

    # Write ...

    # Header
    f.write(b"\x89PNG\x0d\x0a\x1a\x0a")

    # First chunk
    w, h = shape[1], shape[0]
    depth = 8
    ctyp = 0b0110 if shape[2] == 4 else 0b0010
    ihdr = struct.pack(">IIBBBBB", w, h, depth, ctyp, 0, 0, 0)
    add_chunk(ihdr, "IHDR")

    # Chunk with pixels. Just one chunk, no fancy filters.
    compressor = zlib.compressobj(level=7)
    compressed_data = []
    for row_index in range(shape[0]):
        row = array[row_index]
        compressed_data.append(compressor.compress(b"\x00"))  # prepend filter byter
        compressed_data.append(compressor.compress(row))
    compressed_data.append(compressor.flush())
    add_chunk(b"".join(compressed_data), "IDAT")

    # Closing chunk
    add_chunk(b"", "IEND")

    if file is None:
        return f.getvalue()
