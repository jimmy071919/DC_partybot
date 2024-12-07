#!/bin/bash

# Install FFmpeg if needed
apt-get update && apt-get install -y ffmpeg

# Keep the service running
python main.py & 
while true; do sleep 86400; done
