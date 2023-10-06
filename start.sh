#!/bin/sh
# filename: start.sh
pip install -r requirements.txt > requirements.log
path="$PWD"
python3 "$path"/pip-updater.py -h