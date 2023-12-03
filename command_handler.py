import questionary
from typing import Callable
from rich.console import Console
from command import Command

console = Console()


class CommandHandler:
    """
    Class for command handling
    """

    commands: list[Command]

    def __init__(self):
        self.commands = []

    def add_command(self, name: str, description: str, handler: Callable[[], None]):
        """
        Add a command to the command list
        """
        self.commands.append(Command(name, description, handler))

    def get_commands(self) -> list[Command]:
        """
        Get all commands
        """
        return self.commands

    def get_command(self, name: str) -> Command:
        """
        Get a command by name
        """
        for command in self.commands:
            if command.name == name:
                return command

        return None

    def show_command_chooser(self):
        """
        Show a command chooser
        """

        try:
            answer = questionary.select(
                "select a command",
                choices=list(self.__get_choises()),
                use_shortcuts=True).ask()

            if not answer:
                return True

            return self.run_command(answer)
        except KeyboardInterrupt:
            return True

    def run_command(self, name: str):
        """
        Run a command by name
        """
        command = self.get_command(name)
        if command:
            try:
                return command.handler()
            except Exception as e:
                console.print(e)
                questionary.press_any_key_to_continue("press any key to continue").ask()
        else:
            raise Exception("Command not found")

    def __get_choises(self) -> list[str]:
        """
        Get a list of choises for the command chooser
        """

        for command in self.commands:
            choise = questionary.Choice(
                title=f"{command.name.ljust(15)}{command.description}",
                value=command.name)

            yield choise
