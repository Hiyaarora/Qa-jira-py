import sys

from rich.console import Console

console = Console()


def print_help() -> None:
    console.print("\n[cyan]  jira[/cyan][dim] — QA Jira CLI[/dim]\n")
    console.print("  [green]jira setup[/green]          [dim]First-time configuration[/dim]")
    console.print("  [green]jira task create[/green]    [dim]Create a daily QA task[/dim]")
    console.print("  [green]jira mk bug[/green]         [dim]Create a bug with AI-structured description[/dim]")
    console.print("  [green]jira mk bugsheet[/green]    [dim]Export bugs in an epic to a local Excel file[/dim]")
    console.print("  [green]jira rm <ID|URL>[/green]    [dim]Delete a Jira issue by key or URL[/dim]\n")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        return
    console.print(f"[red]Unknown command: {' '.join(args)}[/red]")
    print_help()
    sys.exit(1)
