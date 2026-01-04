# Contributing
Contributions of are encouraged and greatly appreciated.

## Getting Started
Code must pass the following CI checks before it will be accepted:
- Be preformatted with [black](https://github.com/psf/black)
- A mypy type hinting check
- A pylint check (including full docstring coverage)
- shphinx linkcheck, spelling and doctest (code snippet tests)
- Unit and end-to-end tests

Most of these checks can be run locally using [pre-commit](https://pre-commit.com/). To configure this run:
```bash
pip install pre-commit
pre-commit install
```
pylint, mypy and formatting checks will then be automatically run as part of your git hooks. sphinx tests can also be run by pre-commit, though you must first install some additional dependencies to build the documentation:
```bash
pip install -r docs/requirements.txt
sudo apt-get install enchant-2 # This depends on your distribution- for more see the pyenchant documentation
```
You can then run all pre-commit checks manually:
```bash
pre-commit run --hook-stage manual --all-files
```

For instructions on running tests locally please consult the respective markdown files- this process more more complex since bluez, dbus and the hci_vhci kernel module are required.