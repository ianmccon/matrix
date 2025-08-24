#!/bin/bash

# Activate virtual environment
source /home/pi/matrix/venv/bin/activate

# Change to working directory change this if not following along with our repo
cd /home/pi/matrix

# Start Gunicorn with Uvicorn worker over a Unix socket
exec gunicorn -c gunicorn_conf.py app:app
 
