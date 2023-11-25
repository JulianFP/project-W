# Welcome to project W

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/JulianFP/project-W/ci.yml?branch=main)](https://github.com/JulianFP/project-W/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/project-W/badge/)](https://project-W.readthedocs.io/)
[![codecov](https://codecov.io/gh/JulianFP/project-W/branch/main/graph/badge.svg)](https://codecov.io/gh/JulianFP/project-W)

## Installation

The Python package `project_W` can be installed from PyPI:

```
python -m pip install project_W
```

## Development installation

If you want to contribute to the development of `project_W`, we recommend
the following editable installation from this repository:

```
git clone git@github.com:JulianFP/project-W.git
cd project-W
python -m pip install --editable .[tests]
```

Having done so, the test suite can be run using `pytest`:

```
python -m pytest
```

## Acknowledgments

This repository was set up using the [SSC Cookiecutter for Python Packages](https://github.com/ssciwr/cookiecutter-python-package).
