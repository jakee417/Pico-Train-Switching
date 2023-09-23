#!/bin/bash
RED='\033[0;31m'
NC='\033[0m'
BLUE='\033[0;34m'
BGreen='\033[1;32m'
ADAFRUIT=adafruit-ampy

# Check to see if adafruit-ampy is installed.
installed=$(pip3 freeze | grep $ADAFRUIT)
if [[ $(echo $installed | wc -w) -eq 0 ]]; then
    echo -e "${BLUE}$ADAFRUIT not installed, installing now${NC}"
    pip3 install $ADAFRUIT
fi

# Start the file copy to a serial connection.
export AMPY_PORT="$(ls /dev/tty.usbmodem*)"

echo -e "${BLUE}🗑️  Reset build files${NC}"
# Clear directories on the board
_=$(ampy rmdir / 2>&1)
# Make sure directories already exist.
_=$(ampy mkdir bin 2>&1)
_=$(ampy mkdir bin/lib 2>&1)

files=$(find bin | grep .mpy)
# Add the main.py to autoboot the API
files=$(echo $files "main.py")
total="$(echo $files | wc -w | tr -d ' ')"
echo -e "${BLUE}Copying [$total] files${NC}"
# Use ampy to upload files from the source directory to the Pico
i=0
j=0
for file in $files; do
copy_result=$(ampy put "$file" "$file" 2>&1)
if [[ -n $copy_result ]]; then
    echo -e "🔨 ${RED}$file ❌"
    echo -e $copy_result${NC}
    ((j=j+1))
else
    echo "🔨 $file ✅"
    ((i=i+1))
fi
done

echo -e "${BGreen}----------------------------------"
echo "Copy Report:"
echo "----------------------------------"
echo "[$i / $total] file copies ✅ "
echo "[$j / $total] file errors ❌"
echo -e "----------------------------------${NC}"
exit 0
