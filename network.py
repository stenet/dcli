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
        handler.add_command("ls", "list all networks", cmd_ls)
        handler.add_command("prune", "prune all unused networks", cmd_prune)
        handler.add_command("rm", "remove a network", cmd_rm)

        if handler.show_command_chooser():
            return False


def __show_header():
    utils.header("networks")


def __get_table(print_table=True):
    table = Table(expand=True)
    table.add_column("id")
    table.add_column("driver")
    table.add_column("name")

    for network in sorted(client.networks.list(), key=lambda c: c.name):
        table.add_row(
            network.short_id, 
            network.attrs.get("Driver"),
            network.name)

    if print_table:
        console.print(table)

    return table


def __get_network_names():
    return [network.name for network in client.networks.list()]


def __get_auto_complete_network():
    __get_table()

    network_name = questionary.autocomplete(
        "select a network",
        choices=__get_network_names(),
        style=styles.autocomplete,
        validate=lambda v: not v or v in __get_network_names()).ask()

    if not network_name:
        return None

    return client.networks.get(network_name)


def cmd_ls():
    """list all networks"""
    RefreshUntilKeyPressed(console, __show_header, lambda: __get_table(print_table=False))


def cmd_prune():
    """prune all unused networks"""
    answer = questionary.confirm("are you sure you want to prune all unused networks?").ask()
    if not answer:
        return

    with console.status("pruning networks..."):
        client.networks.prune()


def cmd_rm():
    """remove a network"""
    network = __get_auto_complete_network()
    if not network:
        return

    with console.status("removing network..."):
        network.remove()
