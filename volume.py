from rich.console import Console
from rich.table import Table
import docker
import questionary
from command_handler import CommandHandler
from refresh import RefreshUntilKeyPressed
import utils
import styles

console = Console()
client = docker.from_env()


def start():
    """initial menu"""

    while True:
        __show_header()

        handler = CommandHandler()
        handler.add_command("back", "go back", lambda: True)
        handler.add_command("ls", "list all volumes", cmd_ls)
        handler.add_command("prune", "prune all unused volumes", cmd_prune)
        handler.add_command("rm", "remove a volume", cmd_rm)

        if handler.show_command_chooser():
            return False


def __show_header():
    utils.header("volumes")


def __get_table(print_table=True):
    table = Table(expand=True)
    table.add_column("id")
    table.add_column("driver")
    table.add_column("name")

    for volume in sorted(client.volumes.list(), key=lambda c: c.name):
        table.add_row(
            volume.short_id,
            volume.attrs.get("Driver"),
            volume.name)

    if print_table:
        console.print(table)

    return table


def __get_volume_names():
    return [volume.name for volume in client.volumes.list()]


def __get_auto_complete_volume():
    volume_names = __get_volume_names()

    if len(volume_names) == 0:
        console.print("no volumes found")

        questionary.press_any_key_to_continue("press any key to continue").ask()

        return None

    __get_table()

    volume_name = questionary.autocomplete(
        "select a volume",
        choices=volume_names,
        style=styles.autocomplete,
        validate=lambda v: not v or v in __get_volume_names()).ask()

    if not volume_name:
        return None

    return client.volumes.get(volume_name)


def cmd_ls():
    """list all volumes"""
    RefreshUntilKeyPressed(console, __show_header, lambda: __get_table(print_table=False))


def cmd_prune():
    """prune all unused volumes"""
    answer = questionary.confirm("are you sure you want to prune all unused volumes?").ask()
    if not answer:
        return

    with console.status("pruning volumes..."):
        client.volumes.prune()


def cmd_rm():
    """remove a volume"""
    volume = __get_auto_complete_volume()
    if not volume:
        return

    with console.status("removing volume..."):
        volume.remove()
