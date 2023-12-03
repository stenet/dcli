from rich.console import Console
import docker
import questionary
from command_handler import CommandHandler
import utils

console = Console()
client = docker.from_env()


def start():
    """initial menu"""

    while True:
        __show_header()

        handler = CommandHandler()
        handler.add_command("back", "go back", lambda: True)
        handler.add_command("info", "show system info", cmd_info)
        handler.add_command("prune", "prune all unused resources", cmd_prune)
        handler.add_command("version", "show version info", cmd_version)

        if handler.show_command_chooser():
            return False


def __show_header():
    utils.header("system")


def cmd_info():
    """show system info"""
    info = client.info()
    console.print(info)
    questionary.press_any_key_to_continue("press any key to continue").ask()


def cmd_prune():
    """prune all unused resources"""
    answer = questionary.confirm("are you sure you want to prune all unused resources?").ask()
    if not answer:
        return

    with console.status("pruning containers..."):
        client.containers.prune()
    with console.status("pruning networks..."):
        client.networks.prune()
    with console.status("pruning volumes..."):
        client.volumes.prune()
    with console.status("pruning images..."):
        client.images.prune()

def cmd_version():
    """show version info"""
    version = client.version()
    console.print(version)
    questionary.press_any_key_to_continue("press any key to continue").ask()
