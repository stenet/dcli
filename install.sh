sudo chmod +x run.sh

SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
SCRIPTPATH="$SCRIPTPATH/run.sh"

sudo ln -s -f $SCRIPTPATH /usr/local/bin/dcli

python3.12 -m venv env

source env/bin/activate
pip install -r requirements.txt
deactivate