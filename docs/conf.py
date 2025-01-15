"""Configuration script for Sphinx."""

import os
import sys
import json


ROOT_DIR = os.path.abspath(os.path.join(__file__, "..", ".."))
sys.path.insert(0, ROOT_DIR)

import ipywidgets  # noqa: F401, E402

import jupyter_rfb  # noqa: E402


def insert_examples():
    """Copy notebooks from examples dir to docs and create an index."""
    dir1 = os.path.join(ROOT_DIR, "examples")
    dir2 = os.path.join(ROOT_DIR, "docs", "examples")
    # Collect examples
    examples_names = []
    for fname in os.listdir(dir1):
        if fname.endswith(".ipynb") and not fname.startswith("_"):
            examples_names.append(fname)
    examples_names.sort(key=lambda f: "0" + f if f.startswith("hello") else f)
    # Clear current example notebooks
    for fname in os.listdir(dir2):
        if fname.endswith(".ipynb"):
            os.remove(os.path.join(dir2, fname))
    # Copy fresh examples over
    for fname in examples_names:
        # shutil.copy(os.path.join(dir1, fname), os.path.join(dir2, fname))
        with open(os.path.join(dir1, fname), "rb") as f:
            d = json.loads(f.read().decode())
        jupyter_rfb.remove_rfb_models_from_nb(d)
        with open(os.path.join(dir2, fname), "wb") as f:
            f.write(json.dumps(d, indent=2).encode())


insert_examples()


# -- Project information -----------------------------------------------------

project = "jupyter_rfb"
copyright = "2021-2025, jupyter_rfb contributors"
author = "Almar Klein"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "nbsphinx",
]

nbsphinx_execute = "never"
nbsphinx_prolog = """
.. raw:: html

    <style>
    a.jrfb {
        display: inline-block;
        box-sizing: border-box;
        padding: 4px;
        margin: 4px;
        border-radius: 5px;
        border: 1px solid #aaa;
        background: #eee;
        font-size: 85%;
    }
    a.jrfb, a.jrfb:active, a.jrfb:hover {
        color: #000;
        text-decoration: none;
    }
    a.jrfb:hover {
        background: #fafafa;
    }
    </style>

    <div style='float: right'>
        <a class='jrfb'
            href='https://github.com/vispy/jupyter_rfb/tree/main/{{ env.docname }}.ipynb'
            >
        <img width=16 src='../_static/GitHub-Mark-32px.png' />
        View notebook on Github
        </a>

        <a class='jrfb'
            href='{{ env.docname.split("/")[-1] }}.ipynb'
            >
        <img width=16 src='../_static/download-solid.svg' />
        Download
        </a>

        <a class=''
            href='https://mybinder.org/v2/gh/vispy/jupyter_rfb/main?urlpath=lab/tree/{{ env.docname }}.ipynb'
            >
        <img src='https://mybinder.org/badge_logo.svg' />
        </a>

    </div>
    <div style='clear: both; height: 8px;'></div>

"""

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
