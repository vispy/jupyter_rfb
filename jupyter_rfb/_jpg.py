import io


class JpegEncoder:
    """Base JPEG encoder class.

    Subclasses must import their dependencies in their __init__,
    and implement the _encode() method.
    """

    def encode(self, array, quality):
        """Encode the array, returning bytes."""

        quality = int(quality)

        # Check types
        if hasattr(array, "shape") and hasattr(array, "dtype"):
            if array.dtype != "uint8":
                raise ValueError("Image array to convert to JPEG must be uint8")
            original_shape = shape = array.shape
        else:
            raise ValueError(
                f"Invalid type for array, need ndarray-like, got {type(array)}"
            )

        # Check shape
        if len(shape) == 2:
            shape = shape + (1,)
            array = array.reshape(shape)
        if not (len(shape) == 3 and shape[2] in (1, 3)):
            raise ValueError(f"Unexpected image shape: {original_shape}")

        return self._encode(array, quality)

    def _encode(self, array, quality):
        raise NotImplementedError()


class StubJpegEncoder(JpegEncoder):
    """A stub encoder that returns None."""

    def _encode(self, array, quality):
        return None


class SimpleJpegEncoder(JpegEncoder):
    """A JPEG encoder using the simplejpeg library."""

    def __init__(self):
        import simplejpeg

        self.simplejpeg = simplejpeg

    def _encode(self, array, quality):

        # Simplejpeg requires contiguous data
        if not array.flags.c_contiguous:
            array = array.copy()

        # Get appropriate colorspace
        nchannels = array.shape[2]
        if nchannels == 1:
            colorspace = "GRAY"
            colorsubsampling = "Gray"
        elif nchannels == 3:
            colorspace = "RGB"
            colorsubsampling = "444"
        elif nchannels == 4:  # no-cover
            # No alpha in JPEG - transparent pixels become black
            colorspace = "RGBA"
            colorsubsampling = "444"

        # Encode!
        return self.simplejpeg.encode_jpeg(
            array,
            quality=quality,
            colorspace=colorspace,
            colorsubsampling=colorsubsampling,
            fastdct=True,
        )


class PillowJpegEncoder(JpegEncoder):
    """A JPEG encoder using the Pillow library."""

    def __init__(self):
        import PIL.Image

        self.pillow = PIL.Image

    def _encode(self, array, quality):

        # Pillow likes grayscale as an NxM array (not NxMx1)
        if len(array.shape) == 3 and array.shape[2] == 1:
            array = array.reshape(array.shape[:-1])

        # Encode!
        img_pil = self.pillow.fromarray(array)
        f = io.BytesIO()
        img_pil.save(f, format="JPEG", quality=quality)
        return f.getvalue()


def select_encoder():
    """Select an encoder."""

    for cls in [
        SimpleJpegEncoder,  # simplejpeg is fast and lean
        PillowJpegEncoder,  # pillow is commonly available
    ]:
        try:
            return cls()
        except ImportError:
            continue
    else:
        return StubJpegEncoder()  # if all else fails


encoder = select_encoder()


def array2jpg(array, quality=90):
    """Create a JPEG image from a numpy array, with the given quality (percentage).

    The provided array's shape must be either NxM (grayscale), NxMx1 (grayscale),
    or NxMx3 (RGB).

    The encoding is performed be one of multiple possible backends. If
    no backend is available, None is returned.
    """
    return encoder.encode(array, quality)
