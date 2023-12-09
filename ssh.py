import os
from dataclasses import dataclass
import fabric
from rich.console import Console

console = Console()


@dataclass
class Command:
    """SSH command to execute on remote host"""

    command: str
    sudo: bool = False
    hide: bool = True
    status: str = None


def execute_command(host, commands: list[Command]):
    """Call SSH command on remote host and return stdout as string"""
    key_file = os.getenv("SSH_KEY_FILE")
    key_password = os.getenv("SSH_KEY_PASSWORD")
    user = os.getenv("SSH_USER")
    pwd = os.getenv("SSH_PWD")

    if not key_file or not user:
        return "no key or no user"

    if not os.path.exists(key_file):
        return "key file does not exist"
    if not os.path.isfile(key_file):
        return "key file is not a file"

    connect_kwargs = {
        "auth_timeout": 3,
        "timeout": 3,
    }

    if key_file:
        connect_kwargs["key_filename"] = key_file
    if key_password:
        connect_kwargs["passphrase"] = key_password
    if pwd:
        connect_kwargs["password"] = pwd
        connect_kwargs["sudo"] = {"password": "pwd"}

    try:
        client = fabric.Connection( host=host, user=user, connect_kwargs=connect_kwargs)

        def r(cmd):
            if cmd.sudo:
                return client.sudo(cmd.command, hide=cmd.hide)
            else:
                return client.run(cmd.command, hide=cmd.hide)

        result = []
        for command in commands:

            if command.status:
                with console.status(command.status):
                    command_result = r(command)
            else:
                command_result = r(command)

            if not command_result.ok:
                result.append(command_result.stderr.strip())
                continue

            result.append(command_result.stdout.strip())

        return result
    except Exception as e:
        return str(e)
    finally:
        if client:
            client.close()
