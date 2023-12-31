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
        handler.add_command("inspect", "inspect a service", cmd_inspect)
        handler.add_command("logs", "show logs of a service", cmd_logs)
        handler.add_command("ls", "list all services", cmd_ls)
        handler.add_command("rm", "remove a service", cmd_rm)
        handler.add_command("scale", "scale a service", cmd_scale)
        handler.add_command("tag", "change tag of a service image", cmd_tag)
        handler.add_command("tasks", "show tasks of a service", cmd_tasks)
        handler.add_command("update", "force update a service", cmd_update)

        if handler.show_command_chooser():
            return False


def __show_header():
    utils.header("services")


def __get_table(print_table=True):
    table = Table(expand=True)
    table.add_column("id")
    table.add_column("name")
    table.add_column("tag")
    table.add_column("networks")
    table.add_column("ports")
    table.add_column("replicas")
    table.add_column("update status")

    for service in sorted(client.services.list(), key=lambda c: c.name):
        attrs = service.attrs

        spec = attrs["Spec"]
        mode = spec["Mode"]

        tag = spec["TaskTemplate"]["ContainerSpec"]["Image"].split(":", 1)[1]
        tag = tag.split("@", 1)[0]

        replicated = mode.get("Replicated") or mode.get("Global")
        replicas = replicated["Replicas"] if replicated else 0

        update_status = attrs.get("UpdateStatus")
        update_status_state = update_status["State"] if update_status else ""

        endpoint = attrs["Endpoint"]

        running_tasks = 0
        for task in service.tasks():
            if task["Status"]["State"] == "running":
                running_tasks += 1

        color = "green" if running_tasks == replicas else "red"

        table.add_row(
            service.short_id,
            service.name,
            tag,
            __get_networks(endpoint),
            __get_ports(endpoint),
            f"[{color}]{running_tasks}/{replicas}[/]",
            update_status_state)

    if print_table:
        console.print(table)

    return table


def __get_networks(endpoint):
    virtual_ips = endpoint.get("VirtualIPs")

    if not virtual_ips:
        return ""

    networks = []

    for virtual_ip in virtual_ips:
        network_id = virtual_ip["NetworkID"]
        network = client.networks.get(network_id)

        if network.name == "ingress":
            continue

        networks.append(network.name)

    return "\n".join(networks)


def __get_ports(endpoint):
    ports = endpoint.get("Ports")

    if not ports:
        return ""

    port_info = []

    for port in ports:
        port_info.append(f"{port['PublishedPort']} -> {port['TargetPort']}/{port['Protocol']}")

    return "\n".join(port_info)


def __get_service_names():
    return [service.name for service in client.services.list()]


def __get_auto_complete_service(allow_multiple=False):
    service_names = __get_service_names()

    if allow_multiple:
        service_names.append("all")

    if len(service_names) == 0:
        console.print("no services found")
        questionary.press_any_key_to_continue("press any key to continue").ask()

        return None

    __get_table()

    def __is_valid(v):
        if not v:
            return True
        
        if allow_multiple:
            return v == "all" or len([s for s in service_names if s.startswith(v)]) > 0
        else:
            return v in service_names

    service_name = questionary.autocomplete(
        "select services starting with input or 'all'" if allow_multiple else "select a service",
        choices=service_names,
        style=styles.autocomplete,
        validate=__is_valid).ask()

    if not service_name:
        return None

    if service_name == "all":
        return client.services.list()
    elif allow_multiple:
        return [s for s in client.services.list() if s.name.startswith(service_name)]
    else:
        return client.services.get(service_name)


def cmd_inspect():
    """Inspect a service"""
    service = __get_auto_complete_service()

    if not service:
        return

    console.print(service.attrs)
    questionary.press_any_key_to_continue("press any key to continue").ask()


def cmd_logs():
    """Show logs of a service"""
    service = __get_auto_complete_service()

    if not service:
        return

    with console.status("getting logs..."):
        logs = service.logs(
            stdout=True,
            stderr=True,
            tail=100,
            follow=True)

    for log in logs:
        console.print(log.decode("utf-8"), end="")


def cmd_ls():
    """list all services"""
    RefreshUntilKeyPressed(console, __show_header, lambda: __get_table(print_table=False))


def cmd_rm():
    """remove a service"""
    service = __get_auto_complete_service()

    if not service:
        return

    with console.status("removing service..."):
        service.remove()


def cmd_scale():
    """scale a service"""
    services = __get_auto_complete_service(allow_multiple=True)

    if not services:
        return

    replicas = questionary.text(
        "enter the number of replicas",
        default="1",
        validate=lambda v: v.isdigit() and int(v) > 0).ask()

    for service in services:
        with console.status(f"scaling service [orange3]{service.name}[/]..."):
            service.scale(int(replicas))

        console.print(f"  service [orange3]{service.name}[/] scaled")

    cmd_tasks(services)


def cmd_tag():
    """change tag of a service image"""
    services = __get_auto_complete_service(allow_multiple=True)

    if not services:
        return

    image_tag = questionary.text("enter the new tag").ask()
    if not image_tag:
        return

    for service in services:
        with console.status(f"tagging service [orange3]{service.name}[/]..."):
            image_with_digest = service.attrs["Spec"]["TaskTemplate"]["ContainerSpec"]["Image"]
            image_without_tag = image_with_digest.split(":", 1)[0]
            updated_image = f"{image_without_tag}:{image_tag}"
            service.update(image=updated_image)

        console.print(f"  service [orange3]{service.name}[/] tagged")

    cmd_tasks(services)


def cmd_tasks(services=None):
    """show tasks of a service"""
    services = services or __get_auto_complete_service(allow_multiple=True)

    if not services:
        return

    def go():
        table = Table(expand=True)
        table.add_column("updated at")
        table.add_column("node")
        table.add_column("service")
        table.add_column("tag")
        table.add_column("current state")
        table.add_column("desired state")
        table.add_column("error")

        services_and_tasks = [(s, t) for s in services for t in s.tasks()]
        services_and_tasks = sorted(services_and_tasks, key=lambda t: t[1]["UpdatedAt"], reverse=True)
        nodes = client.nodes.list()

        index = 0
        for service_and_task in services_and_tasks:
            service, task = service_and_task

            node_id = task.get("NodeID", None)
            if not node_id:
                continue

            node = next((n for n in nodes if n.id == node_id), None)

            state = task["Status"].get("State")
            desired_state = task.get("DesiredState", "unknown")

            if state == desired_state and state == "shutdown":
                continue

            tag = task["Spec"]["ContainerSpec"]["Image"].split(":", 1)[1]
            tag = tag.split("@", 1)[0]

            color = "green" if state == desired_state else "red"

            table.add_row(
                utils.format_date_time(task["UpdatedAt"]),
                node.attrs.get("Description").get("Hostname"),
                service.name,
                tag,
                f"[{color}]{state}[/]",
                desired_state,
                task["Status"].get("Err"))

            index += 1
            if index > 40:
                break

        return table

    RefreshUntilKeyPressed(console, __show_header, go)


def cmd_update():
    """force update a service"""
    services = __get_auto_complete_service(allow_multiple=True)

    if not services:
        return

    for service in services:
        with console.status(f"updating service [orange3]{service.name}[/]..."):
            image_with_digest = service.attrs["Spec"]["TaskTemplate"]["ContainerSpec"]["Image"]
            image_without_digest = image_with_digest.split("@", 1)[0]

            registry_data = client.images.get_registry_data(image_without_digest)
            digest = registry_data.attrs["Descriptor"]["digest"]
            updated_image = f"{image_without_digest}@{digest}"

            force_update = updated_image != image_with_digest

            if force_update:
                service.update(image=updated_image, force_update=True)
            else:
                service.force_update()

        console.print(f"  service [orange3]{service.name}[/] updated")

    cmd_tasks(services)
