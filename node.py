from threading import Thread
from rich.console import Console
from rich.table import Table
import docker
import questionary
from command_handler import CommandHandler
from refresh import RefreshUntilKeyPressed
import utils
import ssh
import styles

console = Console()
client = docker.from_env()


def start():
    """initial menu"""

    while True:
        __show_header()

        handler = CommandHandler()
        handler.add_command("back", "go back", lambda: True)
        handler.add_command("activate", "activate a node", cmd_activate)
        handler.add_command("drain", "drain a node", cmd_drain)
        handler.add_command("inspect", "inspect a node", cmd_inspect)
        handler.add_command("ls", "list all nodes", cmd_ls)
        handler.add_command("overview", "show an overview of all nodes", cmd_overview)

        if handler.show_command_chooser():
            return False


def __show_header():
    utils.header("nodes")


def __get_table(availability=None, print_table=True):
    table = Table(expand=True)
    table.add_column("id")
    table.add_column("host")
    table.add_column("role")
    table.add_column("availability")

    for node in sorted(client.nodes.list(), key=lambda c: c.attrs.get("Description").get("Hostname")):
        if availability and availability != node.attrs.get("Spec").get("Availability"):
            continue

        attrs = node.attrs
        spec = attrs.get("Spec")
        description = attrs.get("Description")

        color = "green" if spec.get("Availability") == "active" else "red"

        table.add_row(
            node.short_id,
            description.get("Hostname"),
            spec.get("Role"),
            f"[{color}]{spec.get("Availability")}[/]")

    if print_table:
        console.print(table)

    return table


def __get_node_names(availability=None):
    nodes = client.nodes.list()
    node_names = []

    for node in nodes:
        if availability and availability != node.attrs['Spec']['Availability']:
            continue

        node_names.append(node.attrs['Description']['Hostname'])

    return node_names


def __get_auto_complete_node(availability=None):
    node_names = __get_node_names(availability=availability)

    if len(node_names) == 0:
        console.print("no nodes found")
        questionary.press_any_key_to_continue("press any key to continue").ask()

        return None

    __get_table(availability=availability)

    node_name = questionary.autocomplete(
        "select a node",
        choices=node_names,
        style=styles.autocomplete,
        validate=lambda v: not v or v in __get_node_names()).ask()

    if not node_name:
        return None

    return client.nodes.get(node_name)


def cmd_activate():
    """activate a node"""
    node = __get_auto_complete_node("drain")

    if not node:
        return

    with console.status("activating node..."):
        node.update({
            "Availability": "active",
            "Role": node.attrs.get("Spec").get("Role")})


def cmd_drain():
    """drain a node"""
    node = __get_auto_complete_node("active")

    if not node:
        return

    with console.status("draining node..."):
        node.update({
            "Availability": "drain",
            "Role": node.attrs.get("Spec").get("Role")})


def cmd_inspect():
    """Inspect a node"""
    node = __get_auto_complete_node()

    if not node:
        return

    console.print(node.attrs)
    questionary.press_any_key_to_continue("press any key to continue").ask()


def cmd_ls():
    """list all nodes"""
    RefreshUntilKeyPressed(console, __show_header, lambda: __get_table(print_table=False))


def cmd_overview():
    """show an overview of all nodes"""

    stat_dic = {}
    thread = Thread(target=lambda: __load_stats(stat_dic))
    thread.start()

    def go():
        table = Table(expand=True)
        table.add_column("node")
        table.add_column("services")
        table.add_column("stats")

        services = sorted(client.services.list(), key=lambda s: s.name)

        tasks = []
        for service in services:
            tasks.extend([task for task in service.tasks() if task["Status"]["State"] == "running"])

        for node in sorted(client.nodes.list(), key=lambda c: c.attrs.get("Description").get("Hostname")):
            attrs = node.attrs
            hostname = attrs.get("Description").get("Hostname")

            if thread.is_alive():
                stats = "loading..."
            else:
                stats = stat_dic.get(node.id, "not available")

            node_tasks = [task for task in tasks if task["NodeID"] == node.id]
            services_arr = []
            for node_task in node_tasks:
                service = next((s.name for s in services if s.id == node_task["ServiceID"]), None)
                services_arr.append(service)

            table.add_row(
                hostname,
                "\n".join(services_arr),
                stats)

        return table

    RefreshUntilKeyPressed(console, __show_header, go)


def __load_stats(dic):
    for node in client.nodes.list():
        attrs = node.attrs

        node_ip = attrs.get("Status").get("Addr")
        
        # leader
        if node_ip == "0.0.0.0":
            manager_status = attrs.get("ManagerStatus")

            if manager_status and manager_status.get("Leader"):
                node_ip = manager_status.get("Addr")
                node_ip = node_ip.partition(":")[0]

        stats_arr = ssh.execute_command(
            node_ip,
            [
                "df -k | grep /$ | awk '{print $2 \"/\" $3 }'",
                "free --kilo | grep Mem | awk '{print $2 \"/\" $3 }'"
            ])

        if stats_arr and len(stats_arr) == 2:
            disk_arr = stats_arr[0].partition("\n")[0].split("/")
            disk_total = round(int(disk_arr[0]) / 1024 / 1024, 2)
            disk_used = round(int(disk_arr[1]) / 1024 / 1024, 2)
            disk_percent = round(disk_used / disk_total * 100, 2)
            disk_color = "green" if disk_percent < 80 else "red"

            mem_arr = stats_arr[1].partition("\n")[0].split("/")
            mem_total = round(int(mem_arr[0]) / 1024 / 1024, 2)
            mem_used = round(int(mem_arr[1]) / 1024 / 1024, 2)
            mem_percent = round(mem_used / mem_total * 100, 2)
            mem_color = "green" if mem_percent < 80 else "red"

            disk = f"disk: {disk_used}GB/{disk_total}GB [{disk_color}]({disk_percent}%)[/]"
            mem = f"mem: {mem_used}GB/{mem_total}GB [{mem_color}]({mem_percent}%)[/]"
            dic[node.id] = f"{disk}\n{mem}"
