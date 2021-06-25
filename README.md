jupyterfb
===============================

Remote Frame Buffer for Jupyter widgets

Installation
------------

To install use pip:

    $ pip install jupyterfb

For a development installation (requires [Node.js](https://nodejs.org) and [Yarn version 1](https://classic.yarnpkg.com/)),

    $ git clone https://github.com/vispy/jupyterfb.git
    $ cd jupyterfb
    $ pip install -e .
    $ jupyter nbextension install --py --symlink --overwrite --sys-prefix jupyterfb
    $ jupyter nbextension enable --py --sys-prefix jupyterfb

When actively developing your extension for JupyterLab, run the command:

    $ jupyter labextension develop --overwrite jupyterfb

Then you need to rebuild the JS when you make a code change:

    $ cd js
    $ yarn run build

You then need to refresh the JupyterLab page when your javascript changes.
