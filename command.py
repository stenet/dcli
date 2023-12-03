from typing import Callable

class Command:
    """
    Class for commands
    """

    name: str
    description: str
    handler: Callable[[], bool]

    def __init__(self, name: str, description: str, handler: Callable[[], bool]):
        """
        Initialize a command
        """
        self.name = name
        self.description = description
        self.handler = handler
