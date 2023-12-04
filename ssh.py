import os
import paramiko
from rich.console import Console

console = Console()


def execute_command(host, commands):
    """Call SSH command on remote host and return stdout as string"""
    key = os.getenv("SSH_KEY_FILE")
    user = os.getenv("SSH_USER")
    pwd = os.getenv("SSH_PWD")

    if not key or not user:
        return None

    try:
        pkey = paramiko.RSAKey.from_private_key_file(key)

        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, pkey=pkey, username=user, password=pwd, timeout=3, auth_timeout=3)

        result = []
        for command in commands:
            _, _stdout, _ = client.exec_command(command)
            result.append(_stdout.read().decode())

        client.close()
        return result
    except Exception:
        return None
