from __future__ import print_function
from setuptools import setup, find_packages
import os
from os.path import join as pjoin
from distutils import log

from jupyter_packaging import (
    create_cmdclass,
    install_npm,
    ensure_targets,
    combine_commands,
    get_version,
)


here = os.path.dirname(os.path.abspath(__file__))

log.set_verbosity(log.DEBUG)
log.info("setup.py entered")
log.info("$PATH=%s" % os.environ["PATH"])

name = "jupyter_rfb"
LONG_DESCRIPTION = "Remote Frame Buffer for Jupyter"

# Get jupyter_rfb version
version = get_version(pjoin(name, "_version.py"))

js_dir = pjoin(here, "js")

# Representative files that should exist after a successful build
jstargets = [
    pjoin(js_dir, "dist", "index.js"),
]

data_files_spec = [
    ("share/jupyter/nbextensions/jupyter_rfb", "jupyter_rfb/nbextension", "*.*"),
    ("share/jupyter/labextensions/jupyter_rfb", "jupyter_rfb/labextension", "**"),
    ("share/jupyter/labextensions/jupyter_rfb", ".", "install.json"),
    ("etc/jupyter/nbconfig/notebook.d", ".", "jupyter_rfb.json"),
]

cmdclass = create_cmdclass("jsdeps", data_files_spec=data_files_spec)
cmdclass["jsdeps"] = combine_commands(
    install_npm(js_dir, npm=["yarn"], build_cmd="build:prod"),
    ensure_targets(jstargets),
)

setup_args = dict(
    name=name,
    version=version,
    description="Remote Frame Buffer for Jupyter",
    long_description=LONG_DESCRIPTION,
    include_package_data=True,
    install_requires=[
        "numpy", "ipywidgets>=7.6.0",
    ],
    packages=find_packages(),
    zip_safe=False,
    cmdclass=cmdclass,
    author="Almar Klein",
    author_email="almar@almarklein.org",
    license="MIT",
    url="https://github.com/vispy/jupyter_rfb",
    keywords=[
        "ipython",
        "jupyter",
        "widgets",
        "visualization",
        "remote frame buffer",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: IPython",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Multimedia :: Graphics",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)

setup(**setup_args)
