#!/bin/bash
source .venv/bin/activate
files=$(find app | grep "\.py")
for file in $files
do
    python3 -m mpy_cross $file
done
