# jupyter_rfb

Remote Frame Buffer for Jupyter

## Introduction

The `jupyter_rfb` library provides an widget (an ipywidgets subclass)
that can be used in the Jupyter notebook and in JupyterLab to realize
a remote frame-buffer.

Images that are generated at the server are streamed to the client
(Jupyter) where they are shown. Evens (such as mouse interactions) are
streamed in the other direction, where the server can react by generating
new images.

This "remote frame buffer" approach can be an effective method for certain
visualizations to be dispayed in Jupyter notebook/lab. For example
visualization created by tools like vispy, datoviz or pygfx.


## Installation

To install use pip:

    $ pip install jupyter_rfb

On older versions of Jupyter notebook/lab an extra step might be needed
to enable the widget. TODO


## Developers

For a development installation (requires [Node.js](https://nodejs.org) and [Yarn version 1](https://classic.yarnpkg.com/)),

    $ git clone https://github.com/vispy/jupyter_rfb.git
    $ cd jupyter_rfb
    $ pip install -e .
    $ jupyter nbextension install --py --symlink --overwrite --sys-prefix jupyter_rfb
    $ jupyter nbextension enable --py --sys-prefix jupyter_rfb

When actively developing your extension for JupyterLab, run the command:

    $ jupyter labextension develop --overwrite jupyter_rfb

Then you need to rebuild the JS when you make a code change:

    $ cd js
    $ yarn run build

You then need to refresh the JupyterLab page when your javascript changes.


## License

MIT
