# Runner for Project W

[![License: AGPLv3](https://img.shields.io/badge/License-agplv3-yellow.svg)](https://opensource.org/license/agpl-v3)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/JulianFP/project-W-runner/ci.yml?branch=main)](https://github.com/JulianFP/project-W-runner/actions/workflows/ci.yml)

## What is this?
This is the runner for Project-W written in Python. Its job is to process the transcription jobs that the backend assigns to it, which means that the runner is the place where the actual whisper speech-to-text code runs. It has been designed as an http client such that it doesn't have any firewall requirements or similar. All communications between backend and runner are initiated from the runner only! To learn more about Project W (including its runner) and how to install and run it, [visit its documentation](https://project-w.readthedocs.io). Other components of Project W are [the backend](https://github.com/JulianFP/project-W) and [the frontend](https://github.com/JulianFP/project-W-frontend).

## Acknowledgments
This repository was set up using the [SSC Cookiecutter for Python Packages](https://github.com/ssciwr/cookiecutter-python-package).
