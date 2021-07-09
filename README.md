jupyter_rfb
===============================

Remote Frame Buffer for Jupyter

Installation
------------

To install use pip:

    $ pip install jupyter_rfb

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
