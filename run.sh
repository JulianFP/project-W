#!/bin/bash
JWT_SECRET_KEY=$(cat JWT_SECRET_KEY) python -m flask --debug --app 'project_W:create_app()' run