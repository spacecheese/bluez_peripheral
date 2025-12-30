# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import inspect
import importlib
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../../"))

# -- Project information -----------------------------------------------------

project = "bluez-peripheral"
copyright = "{}, spacecheese".format(datetime.now().year)
author = "spacecheese"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinxcontrib.spelling",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.linkcode",
    "sphinx.ext.doctest",
    "sphinx_inline_tabs",
    "sphinx_mdinclude",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

nitpicky = True

autodoc_typehints = "description"

linkcheck_timeout = 10

# -- Linkcode ----------------------------------------------------------------
def _get_git_ref():
    try:
        ref = (
            subprocess.check_output(["git", "describe", "--tags", "--exact-match"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except subprocess.CalledProcessError:
        ref = (
            subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    return ref

GIT_REF = _get_git_ref()

def linkcode_resolve(domain, info):
    if domain != "py":
        return None

    modname = info.get("module")
    fullname = info.get("fullname")
    if not modname:
        return None

    obj = importlib.import_module(modname)
    for part in fullname.split("."):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            return None

    try:
        src = inspect.getsourcefile(obj)
        lines, lineno = inspect.getsourcelines(obj)
    except Exception:
        return None
    
    if src is None:
        return None

    src = Path(src).relative_to(Path(__file__).parents[2])

    return (
        f"https://github.com/spacecheese/bluez_peripheral/"
        f"blob/{GIT_REF}/{src.as_posix()}#L{lineno}-L{lineno+len(lines)-1}"
    )

# -- Napoleon ----------------------------------------------------------------
napoleon_numpy_docstring = False

# -- Intersphinx -------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "dbus_fast": ("https://dbus-fast.readthedocs.io/en/latest/", None),
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# # Add any paths that contain custom static files (such as style sheets) here,
# # relative to this directory. They are copied after the builtin static files,
# # so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

# -- Options for spelling checker --------------------------------------------
spelling_lang = "en_US"
tokenizer_lang = "en_US"
