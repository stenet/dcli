from rich.console import Console
from rich.table import Table
import docker
import questionary
from command_handler import CommandHandler
from refresh import RefreshUntilKeyPressed
import utils

console = Console()
client = docker.from_env()


def start():
    """initial menu"""

    while True:
        __show_header()

        handler = CommandHandler()
        handler.add_command("back", "go back", lambda: True)
        handler.add_command("ls", "list all images", cmd_ls)
        handler.add_command("prune", "prune all unused images", cmd_prune)

        if handler.show_command_chooser():
            return False

def __show_header():
    utils.header("images")


def __get_table(print_table=True):
    table = Table(expand=True)
    table.add_column("id")
    table.add_column("name")
    table.add_column("created at")

    for image in sorted(client.images.list(), key=lambda c: " ".join(c.tags)):
        table.add_row(
            image.short_id,
            " ".join(image.tags),
            utils.format_date_time(image.attrs["Created"]))

    if print_table:
        console.print(table)

    return table


def cmd_ls():
    """list all images"""
    RefreshUntilKeyPressed(console, __show_header, lambda: __get_table(print_table=False))


def cmd_prune():
    """prune all unused images"""
    answer = questionary.confirm("are you sure you want to prune all unused images?").ask()

    if not answer:
        return

    with console.status("pruning images..."):
        client.images.prune()
