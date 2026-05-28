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

    cmd, *rest = args
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
            console.print("[red]Usage: jira rm <ISSUE-KEY or URL>[/red]")
            sys.exit(1)
        from qa_jira.commands.rm import run as rm_run

        rm_run(target)
    else:
        console.print(f"[red]Unknown command: {' '.join(args)}[/red]")
        print_help()
        sys.exit(1)
