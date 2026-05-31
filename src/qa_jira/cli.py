import sys

import questionary
from rich.console import Console

console = Console()

_MENU = [
    questionary.Choice("Create a daily QA task",              "task create"),
    questionary.Choice("File a bug with AI description",      "mk bug"),
    questionary.Choice("Export epic bugs to Excel",           "mk bugsheet"),
    questionary.Choice("Delete a Jira issue",                 "rm"),
    questionary.Choice("Setup / reconfigure",                 "setup"),
    questionary.Choice("Exit",                                "exit"),
]


def _run_command(cmd: str, rest: list[str]) -> None:
    if cmd == "setup":
        from qa_jira.commands.setup import run as setup_run
        setup_run()
    elif cmd == "task" and rest and rest[0] == "create":
        from qa_jira.commands.task_create import run as task_run
        task_run()
    elif cmd == "mk" and rest and rest[0] == "bug":
        from qa_jira.commands.mk_bug import run as bug_run
        bug_run()
    elif cmd == "mk" and rest and rest[0] == "bugsheet":
        from qa_jira.commands.mk_bugsheet import run as bs_run
        bs_run()
    elif cmd == "rm":
        target = rest[0] if rest else None
        if not target:
            target = questionary.text("Issue key or URL to delete:").ask()
            if not target:
                return
        from qa_jira.commands.rm import run as rm_run
        rm_run(target.strip())
    else:
        console.print(f"[red]Unknown command: {cmd} {' '.join(rest)}[/red]")


def _interactive_menu() -> None:
    console.print("\n[cyan]  jira[/cyan][dim] — QA Jira CLI[/dim]\n")
    while True:
        choice = questionary.select(
            "What do you want to do?",
            choices=_MENU,
        ).ask()

        if choice is None or choice == "exit":
            break

        parts = choice.split()
        _run_command(parts[0], parts[1:])
        console.print()  # blank line between commands


def main() -> None:
    args = sys.argv[1:]

    # No args → interactive menu
    if not args or args[0] in ("-h", "--help", "help"):
        _interactive_menu()
        return

    cmd, *rest = args
    _run_command(cmd, rest)
