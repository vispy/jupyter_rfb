# jupyter_rfb

Remote Frame Buffer for Python notebooks

[![PyPI version](https://badge.fury.io/py/jupyter-rfb.svg)](https://badge.fury.io/py/jupyter-rfb)
[![CI](https://github.com/vispy/jupyter_rfb/actions/workflows/ci.yml/badge.svg)](https://github.com/vispy/jupyter_rfb/actions)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/vispy/jupyter_rfb/main?urlpath=lab/tree/examples/hello_world.ipynb)

## Introduction

The `jupyter_rfb` library provides a widget (an `anywidget` subclass)
that can be used in various notebook environments to implement
a remote frame-buffer.

Images that are generated at the server are streamed to the notebook
where they are shown. Standardized [events](https://pygfx.org/renderview/) (such as mouse interactions) are
streamed in the other direction, where the server can react by
generating new images.

This *remote-frame-buffer* approach is an effective method for
server-generated visualizations to be dispayed in notebook environments. For
example visualizations created by tools like vispy, datoviz, and pygfx.


## Scope

The above defines the full scope of this library; it's a base widget
that other libraries can extend for different purposes.


## Installation

Jupyter_rfb requires Python 3.9 or higher. You can install it via pip:

    $ pip install jupyter_rfb


## Developer notes

See [the contributor guide](https://jupyter-rfb.readthedocs.io/en/stable/contributing.html) on how to install ``jupyter_rfb``
in a dev environment, and on how to contribute.


## License

MIT
