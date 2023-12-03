#!/usr/bin/bash

p="$(dirname "$(readlink -f "$0")")"
cd $p
echo "$(pwd)"

source env/bin/activate
python3.12 main.py
