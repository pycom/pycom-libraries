#!/bin/bash
set -e
#set -x
SOURCE="$(dirname $0)"
if [ -z $1 ]; then
  echo "usage: $0 micropython_firmware_directory"
  exit 1
fi
if [ ! -d $1/esp32/frozen/Common ]; then
  echo "Need to specify valid micropython firmware directory!"
  exit 1
fi
if [ ! -d $SOURCE ]; then
  echo "Can't find source directory $SOURCE"
  exit 1
fi

# moving main
# if [ -d $1/esp32/frozen/Pybytes ]; then
#     cp $SOURCE/main.py $1/esp32/frozen/Pybytes/_main.py
#     cp $1/esp32/frozen/Base/_boot.py $1/esp32/frozen/Pybytes/ 
# elif [ -d $1/esp32/frozen/Base ]; then
#     cp $SOURCE/main.py $1/esp32/frozen/Base/_main.py
# else
#     cp $SOURCE/main.py $1/esp32/frozen/_main.py
# fi

for i in $SOURCE/lib/*.py; do
  SRC=$i
  FN=$(basename $i)
  cp $SRC $1/esp32/frozen/Common/_$FN
done

cp -r $SOURCE/lib/msgpack $1/esp32/frozen/Common/
echo "Done copying Pymesh library to $1/esp32/frozen/Common/"