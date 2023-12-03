from os import system
from rich.console import Console
from rich.markdown import Markdown
import dateutil.parser

console = Console()


def header(text):
    """print a header"""
    clear()
    markdown = Markdown(f"# {text}")
    console.print(markdown, style="orange3 on grey15")
    console.print()


def clear():
    """clear the screen"""
    system("clear")


def format_date_time(dt):
    """format a datetime string"""
    return dateutil.parser.parse(dt).strftime("%d.%m.%Y %H:%M")
