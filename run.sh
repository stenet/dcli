#!/usr/bin/bash

# export SSH_USER="stefan"
# export SSH_PWD=""
# export SSH_KEY_FILE="/home/stefan/.ssh/id_rsa"

p="$(dirname "$(readlink -f "$0")")"
cd $p
echo "$(pwd)"

source env/bin/activate
python3.12 main.py
