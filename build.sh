#!/bin/bash
source .venv/bin/activate
files=$(find src | grep "\.py")
for file in $files
do
    newfile=$(echo $file | sed "s+src/+bin/+" | sed "s+.py+.mpy+")
    python3 -m mpy_cross $file -o $newfile
    echo 🔨 $newfile
done
