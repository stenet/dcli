#!/usr/bin/env python3.12

from rich.console import Console
from rich.traceback import install
from command_handler import CommandHandler
import utils
import container
import image
import network
import node
import service
import volume
import system

install()
console = Console()


def start():
    """initial menu"""

    while True:
        utils.header("docker interactive cli")

        handler = CommandHandler()
        handler.add_command("exit", "exit the program", exit)
        handler.add_command("container", "manage containers", container.start)
        handler.add_command("image", "manage images", image.start)
        handler.add_command("network", "manage networks", network.start)
        handler.add_command("node", "manage nodes", node.start)
        handler.add_command("service", "manage services", service.start)
        handler.add_command("volume", "manage volumes", volume.start)
        handler.add_command("system", "system info and manage", system.start)

        if handler.show_command_chooser():
            break


start()
