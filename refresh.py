from time import sleep
from typing import Callable
from threading import Event
import concurrent.futures
from rich.console import Console
from rich.live import Live

class RefreshUntilKeyPressed:
    """Call for repeating an action until a key is pressed"""
    header_callback: Callable
    console: Console
    callback: Callable
    event: Event

    def __init__(self, console: Console, header_callback: Callable, callback: Callable):
        self.console = console
        self.header_callback = header_callback
        self.callback = callback
        self.event = Event()

        self.__wait_for_any_key()

    def __wait_for_any_key(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.__run)

            try:
                result = input()
                self.event.set()
                future.result()

                if result == "s":
                    self.header_callback()
                    self.console.print("Press [orange3]Enter-Key[/] to exit.", style="bold")
                    self.console.print(self.callback())
                    input()

            except KeyboardInterrupt:
                self.event.set()
                future.result()

    def __run(self):
        self.header_callback()
        self.console.print("Press [orange3]Enter-Key[/] to exit or [orange3]s + Enter-Key[/] to stop refreshing.", style="bold")

        with Live(self.callback(), console=self.console, auto_refresh=False) as live:
            while not self.event.is_set():
                sleep(1)

                if self.event.is_set():
                    break

                live.update(self.callback(), refresh=True)
