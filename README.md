# Docker Interactive CLI

I'm still at the beginning with Python. So bear with me if the code is not 100% perfect.

The motivation for creating this tool is that I work a lot with Docker and Docker Swarm and I have to type a lot in the console, which is sometimes a bit tedious - especially when the service names are a bit longer.

![Sceenshot](/assets/dcli-screenshot.png)

The application is based on the Docker SDK for Python. The following functions are supported:

**Container**
exec, inspect, logs, ls, prune, restart, rm, start, stop, stats, stop

**Image**
ls, prune

**Network**
ls, prune, rm

**Node**
activate, drain, inspect, ls, overview

**Service**
inspect, logs, ls, rm, scale, task, force upate

**Volume**
ls, prune, rm

**System**
info, prune, version

## Using docker

```bash
sudo docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock stefanheim/dcli
```

or the more complex one if you want the nodes stats in the overview

```bash
sudo docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock -v /home/xxx/.ssh/id_rsa:/opt/.ssh/id_rsa -e SSH_USER=xxx -e SSH_KEY_FILE=/opt/.ssh/id_rsa stefanheim/dcli
```

## Manual installation

Python 3.12 is required!

Clone the repository:

```bash
git clone https://github.com/stenet/dcli
cd dcli
```

Execute the install-script. This will create a virtual Python environment, install all packages 
using pip and create a symlink `dcli` in `usr/local/bin`.

```bash
./install.sh
```

Run it using `dcli` with sudo:

```bash
sudo dcli
```

## Node overview

If the following enviroment variables are exported, the overview will include disk
and mem information.

```bash
export SSH_USER="xxx"
export SSH_KEY_FILE="/home/xxx/.ssh/id_rsa"

export SSH_PWD="" # optional
```