# jupyter_rfb

Remote Frame Buffer for Jupyter

[![PyPI version](https://badge.fury.io/py/jupyter-rfb.svg)](https://badge.fury.io/py/jupyter-rfb)
[![CI](https://github.com/vispy/jupyter_rfb/actions/workflows/ci.yml/badge.svg)](https://github.com/vispy/jupyter_rfb/actions)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/vispy/jupyter_rfb/main?urlpath=lab/tree/examples/hello_world.ipynb)

## Introduction

The `jupyter_rfb` library provides a widget (an `ipywidgets` subclass)
that can be used in the Jupyter notebook and in JupyterLab to implement
a remote frame-buffer.

Images that are generated at the server are streamed to the client
(Jupyter) where they are shown. Events (such as mouse interactions) are
streamed in the other direction, where the server can react by
generating new images.

This *remote-frame-buffer* approach can be an effective method for
server-generated visualizations to be dispayed in Jupyter notebook/lab. For
example visualization created by tools like vispy, datoviz or pygfx.


## Scope

The above defines the full scope of this library; it's a base widget
that other libraries can extend for different purposes. Consequently,
these libraries don't have to each invent a Jupyter widget, and in
*this* library we can focus on doing that one task really well.


## Installation

To install use pip:

    $ pip install jupyter_rfb

For better performance, also ``pip install simplejpeg`` or ``pip install pillow``.
On older versions of Jupyter notebook/lab an extra step might be needed
to enable the widget.

To install into an existing conda environment:

    $ conda install -c conda-forge jupyter-rfb


## Developer notes

See [the contributor guide](https://jupyter-rfb.readthedocs.io/en/latest/contributing.html) on how to install ``jupyter_rfb``
in a dev environment, and on how to contribute.


## License

MIT
