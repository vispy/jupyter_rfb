The jupyter_rfb contributor guide
=================================

This page is for those who plan to hack on ``jupyter_rfb`` or make other contributions.


How can I contribute?
---------------------

Anyone can contribute to ``jupyter_rfb``. We strive for a welcoming environment -
see our `code of conduct <https://github.com/vispy/vispy/blob/main/CODE_OF_CONDUCT.md>`_.

Contribution can vary from reporting bugs, suggesting improvements,
help improving documentations. We also welcome improvements in the code and tests.
We uphold high standards for the code, and we'll help you achieve that.


Install jupyter_rfb in development mode
---------------------------------------

For a development installation (requires Node.js and Yarn):

.. code-block::

    $ git clone https://github.com/vispy/jupyter_rfb.git
    $ cd jupyter_rfb
    $ pip install -e .
    $ jupyter nbextension install --py --symlink --overwrite --sys-prefix jupyter_rfb
    $ jupyter nbextension enable --py --sys-prefix jupyter_rfb

When actively developing the JavaScript code, run the command:

.. code-block::

    $ jupyter labextension develop --overwrite jupyter_rfb

Then you need to rebuild the JS when you make a code change:

.. code-block::

    $ cd js
    $ yarn run build

You then need to refresh the JupyterLab page when your javascript changes.


Install developer tools
-----------------------

.. code-block::

    $ pip install ruff pytest

Install dependencies required for tests
---------------------------------------

.. code-block::

   $ pip install pillow simplejpeg

Automated tools
---------------

To make it easier to keep the code valid and clean, we use the following tools:

* Run ``ruff format`` to autoformat the code.
* Run ``ruff check`` for linting and formatting checks.
* Run ``python release.py`` to do a release (for maintainers only).


Autocommit hook
---------------

Optionally, you can setup an autocommit hook to automatically run these on each commit:

.. code-block::

    $ pip install pre-commit
    $ pre-commit install
