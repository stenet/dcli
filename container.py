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
        handler.add_command("exec", "execute a command in a container", cmd_exec)
        handler.add_command("inspect", "inspect a container", cmd_inspect)
        handler.add_command("logs", "show logs of a container", cmd_logs)
        handler.add_command("ls", "list all containers", cmd_ls)
        handler.add_command("prune", "prune all stopped containers", cmd_prune)
        handler.add_command("restart", "restart a container", cmd_restart)
        handler.add_command("rm", "remove a container", cmd_rm)
        handler.add_command("start", "start a container", cmd_start)
        handler.add_command("stats", "show stats of a container", cmd_stats)
        handler.add_command("stop", "stop a container", cmd_stop)

        if handler.show_command_chooser():
            return False


def __show_header():
    utils.header("containers")

def __get_table(running_containers_only=True, print_table=True):
    table = Table(expand=True)
    table.add_column("id")
    table.add_column("image", max_width=30)
    table.add_column("name")
    table.add_column("networks")
    table.add_column("ports")
    table.add_column("started at")
    table.add_column("status")

    filters = {
        "status": "running" if running_containers_only else "exited"
    }

    for container in sorted(client.containers.list(filters=filters), key=lambda c: c.name):
        attrs = container.attrs

        image = attrs["Config"]["Image"]

        started_at = utils.format_date_time(attrs["State"]["StartedAt"])

        color = "green" if running_containers_only else "red"

        table.add_row(
            container.short_id,
            image,
            container.name,
            __get_networks(attrs),
            __get_ports(attrs),
            started_at,
            f"[{color}]{container.status}[/]")

    if print_table:
        console.print(table)

    return table


def __get_ports(attrs):
    ports = attrs["NetworkSettings"]["Ports"]
    port_info = []

    for _, (k, v) in enumerate(ports.items()):
        if not v:
            continue

        port_info.append(f"{', '.join(set(map(lambda x: x["HostPort"], v)))} -> {k}")

    return "\n".join(port_info)


def __get_networks(attrs):
    networks = []
    for _, (k, _) in enumerate(attrs["NetworkSettings"]["Networks"].items()):
        networks.append(k)

    return "\n".join(networks)


def __get_container_names():
    return [container.name for container in client.containers.list(all=True)]


def __get_auto_complete_container(running=True):
    container_names = __get_container_names()

    if len(container_names) == 0:
        console.print("no containers found")
        questionary.press_any_key_to_continue("press any key to continue").ask()

        return None

    __get_table(running)

    container_name = questionary.autocomplete(
        "select a container",
        choices=container_names,
        style=styles.autocomplete,
        validate=lambda v: not v or v in __get_container_names()).ask()

    if not container_name:
        return None

    return client.containers.get(container_name)


def cmd_exec():
    """Execute a command in a container"""
    container = __get_auto_complete_container()

    if not container:
        return

    while True:
        cmd = questionary.text("enter command to execute").ask()

        if not cmd or cmd == "exit":
            return

        with console.status("executing command..."):
            stream = container.exec_run(cmd, stream=True, tty=True)

        for line in stream.output:
            console.print(line.decode("utf-8"), end="")

        console.print()


def cmd_inspect():
    """Inspect a container"""
    container = __get_auto_complete_container()

    if not container:
        return

    console.print(container.attrs)
    questionary.press_any_key_to_continue("press any key to continue").ask()


def cmd_logs():
    """Show logs of a container"""
    container = __get_auto_complete_container()

    if not container:
        return

    with console.status("getting logs..."):
        logs = container.logs(
            tail=100,
            follow=True,
            stream=True)

    for log in logs:
        console.print(log.decode("utf-8"), end="")


def cmd_ls():
    """List all containers"""
    RefreshUntilKeyPressed(console, __show_header, lambda: __get_table(print_table=False))


def cmd_prune():
    """Prune all stopped containers"""
    answer = questionary.confirm("are you sure you want to prune all stopped containers?").ask()
    if not answer:
        return

    with console.status("pruning containers..."):
        client.containers.prune()


def cmd_restart():
    """Restart a container"""
    container = __get_auto_complete_container()

    if not container:
        return

    with console.status("restarting container..."):
        container.restart()


def cmd_rm():
    """Remove a container"""
    container = __get_auto_complete_container()

    if not container:
        return

    with console.status("removing container..."):
        container.remove(force=True)


def cmd_start():
    """Start a container"""
    container = __get_auto_complete_container(running=False)

    if not container:
        return

    with console.status("starting container..."):
        container.start()


def cmd_stats():
    """Show stats of a container"""
    container = __get_auto_complete_container()

    if not container:
        return

    with console.status("getting stats..."):
        stats = container.stats(stream=False)

    console.print(stats)
    questionary.press_any_key_to_continue("press any key to continue").ask()


def cmd_stop():
    """Stop a container"""
    container = __get_auto_complete_container()

    if not container:
        return

    with console.status("stopping container..."):
        container.stop()
