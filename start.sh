#!/bin/bash

# Keep the service running
python main.py & 
while true; do sleep 86400; done
