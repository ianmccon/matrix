#!/bin/bash

# Activate virtual environment
source /home/r2d2/matrix/venv/bin/activate

# Change to working directory change this if not following along with our repo
cd /home/r2d2/matrix

# Start Gunicorn with Uvicorn worker over a Unix socket
exec gunicorn -c gunicorn_conf.py app:app
 
