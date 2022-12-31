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
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../../'))

# See https://github.com/sphinx-doc/sphinx/issues/5603
def add_intersphinx_aliases_to_inv(app):
    from sphinx.ext.intersphinx import InventoryAdapter
    inventories = InventoryAdapter(app.builder.env)

    for alias, target in app.config.intersphinx_aliases.items():
        alias_domain, alias_name = alias
        target_domain, target_name = target
        try:
            found = inventories.main_inventory[target_domain][target_name]
            try:
                inventories.main_inventory[alias_domain][alias_name] = found
            except KeyError:
                continue
        except KeyError:
            continue

# -- Project information -----------------------------------------------------

project = "bluez-peripheral"
copyright = "{}, spacecheese".format(datetime.now().year)
author = "spacecheese"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["sphinxcontrib.spelling", "sphinx.ext.autodoc", "sphinx.ext.intersphinx", "sphinx.ext.napoleon", "sphinx_inline_tabs", "m2r2"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

nitpicky = True

# -- Napoleon ----------------------------------------------------------------
napoleon_numpy_docstring = False

# -- Intersphinx -------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "dbus_next": ("https://python-dbus-next.readthedocs.io/en/latest/", None),
}

# Fix resolution of MessageBus class to where docs actually are.
intersphinx_aliases = {
    ('py:class', 'dbus_next.aio.message_bus.MessageBus'):
        ('py:class', 'dbus_next.aio.MessageBus'),
    ('py:class', 'dbus_next.aio.proxy_object.ProxyObject'):
        ('py:class', 'dbus_next.aio.ProxyObject'),
    ('py:class', 'dbus_next.errors.DBusError'):
        ('py:class', 'dbus_next.DBusError'),
    ('py:class', 'dbus_next.signature.Variant'):
        ('py:class', 'dbus_next.Variant'),
}

def setup(app):
    app.add_config_value('intersphinx_aliases', {}, 'env')
    app.connect('builder-inited', add_intersphinx_aliases_to_inv)


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
