# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?= -j auto -W
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

SPHINXDOCOPTS ?= -e
SPHINXDOC     ?= sphinx-apidoc
APIDOCDIR     = source/ref
MODPATH       = ../bluez_peripheral

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

apidoc:
	rm -r "$(APIDOCDIR)"
	@$(SPHINXDOC) -o "$(APIDOCDIR)" "$(MODPATH)" $(SPHINXDOCOPTS)
	rm "$(APIDOCDIR)/modules.rst"

.PHONY: help Makefile apidoc spelling

spelling:
	@$(SPHINXBUILD) -b spelling -W "$(SOURCEDIR)" "$(BUILDDIR)"

autobuild:
	sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
