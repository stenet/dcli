import concurrent.futures
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
        handler.add_command("prune", "Prune all nodes", cmd_prune)

        if handler.show_command_chooser():
            return False


def __show_header():
    utils.header("nodes")


def __get_table(availability=None, print_table=True):
    table = Table(expand=True)
    table.add_column("id")
    table.add_column("host")
    table.add_column("role")
    table.add_column("state")

    for node in sorted(client.nodes.list(), key=lambda c: c.attrs.get("Description").get("Hostname")):
        if availability and availability != node.attrs.get("Spec").get("Availability"):
            continue

        attrs = node.attrs
        spec = attrs.get("Spec")
        description = attrs.get("Description")
        state = attrs.get("Status", {}).get("State")
        av = spec.get("Availability")

        color = "green" if state == "ready" and av == "active" else "red"

        av = f"[{color}]{state}/{av}[/]"

        table.add_row(
            node.short_id,
            description.get("Hostname"),
            spec.get("Role"),
            av)

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

    # no with statement because of concurrent.futures.ThreadPoolExecutor()
    # it would wait for finishing the thread
    stats_future = concurrent.futures.ThreadPoolExecutor().submit(__load_stats, stat_dic)

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

            if stats_future.running():
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


def __get_node_ip(node):
    attrs = node.attrs

    node_ip = attrs.get("Status").get("Addr")

    # leader
    if node_ip == "0.0.0.0":
        manager_status = attrs.get("ManagerStatus")

        if manager_status and manager_status.get("Leader"):
            node_ip = manager_status.get("Addr")
            node_ip = node_ip.partition(":")[0]
    
    return node_ip

def __load_stats(dic):
    for node in client.nodes.list():
        node_ip = __get_node_ip(node)

        stats_arr = ssh.execute_command(
            node_ip,
            [
                ssh.Command("df -k | grep /$ | awk '{print $2 \"/\" $3 }'"),
                ssh.Command("free --kilo | grep Mem | awk '{print $2 \"/\" $3 }'"),
                ssh.Command("uptime -p")
            ])
        
        if isinstance(stats_arr, str):
            dic[node.id] = f"[red]{stats_arr}[/]"
        elif stats_arr and len(stats_arr) == 3:
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
            dic[node.id] = f"[orange3]{stats_arr[2]}[/]\n{disk}\n{mem}"

def cmd_prune():
    """Prune all nodes"""
    if not questionary.confirm("Are you sure?").ask():
        return

    for node in client.nodes.list():
        node_ip = __get_node_ip(node)
        hostname = node.attrs.get("Description").get("Hostname")

        result = ssh.execute_command(
            node_ip,
            [
                ssh.Command(
                    "docker system prune -f", 
                    status=f"pruning node {hostname}",
                    sudo=True)
            ])

        if isinstance(result, str):
            console.print(f"[red]{hostname}:[/] {result}")
            continue 
        elif not result or len(result) != 1:
            console.print(f"[red]{hostname}:[/] error on executing command")
            continue

        console.print(f"[orange3]{hostname}[/]")
        console.print(result[0] or "no output")

    questionary.press_any_key_to_continue("press any key to continue").ask()
    cmd_overview()