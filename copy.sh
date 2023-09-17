#!/bin/bash
RED='\033[0;31m'
NC='\033[0m'
BLUE='\033[0;34m'
BGreen='\033[1;32m'
ADAFRUIT=adafruit-ampy

files=$(find bin | grep .mpy)
total="$(echo $files | wc -w | tr -d ' ')"
echo "----------------------------------"
echo "Copying [$total] files..."
echo "----------------------------------"

echo -e "${BLUE}Running copy from $(pwd)${NC}"

# Check to see if we have access to python3.
python=$(which python3)
if [[ -n $python ]]
then
    echo -e "${BLUE}Using $python to copy code...${NC}" 
else
    echo -e "${RED}python3 not installed. Please install python3 first.${NC}"
    exit 1
fi

# Check to see if adafruit-ampy is installed.
installed=$(pip3 freeze | grep $ADAFRUIT)
if [[ $(echo $installed | wc -w) -eq 0 ]]
then
    echo "----------------------------------"
    echo "$ADAFRUIT not installed, installing now..."
    pip3 install $ADAFRUIT
    echo "----------------------------------"
fi

# Raspberry Pi Pico serial port (update with your Pico's serial port)
SERIAL_PORT="$(ls /dev/tty.usbmodem*)"

i=0
j=0
_=$(ampy --port "$SERIAL_PORT" mkdir bin 2>&1)
_=$(ampy --port "$SERIAL_PORT" mkdir bin/lib 2>&1)
# Use ampy to upload files from the source directory to the Pico
for file in $files
do
copy_result=$(ampy --port "$SERIAL_PORT" put "$file" "$file" 2>&1)
if [[ -n $copy_result ]]
then
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
echo "[$i / $total] file copies ✅"
echo "[$j / $total] file errors ❌"
echo -e "----------------------------------${NC}"
exit 0
