#!/bin/bash
RED='\033[0;31m'
NC='\033[0m'
source .venv/bin/activate
files=$(find src | grep "\.py" | grep -v "\.pyc")
total="$(echo $files | wc -w | tr -d ' ')"
echo "----------------------------------"
echo "Building [$total] files..."
echo "----------------------------------"
for file in $files
do
    newfile=$(echo $file | sed "s+src/+bin/+" | sed "s+.py+.mpy+")
    build_result=$(python3 -m mpy_cross $file -o $newfile 2>&1)
    if [[ -n $build_result ]]
    then
        echo -e "🔨 ${RED}$newfile ❌"
        echo -e $build_result${NC}
    else 
        echo 🔨 $newfile ✅
    fi
done
