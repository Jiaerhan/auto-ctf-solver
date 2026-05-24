"""CLI entry point for auto-ctf-solver."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .agents.base import ChallengeInfo
from .agents.dispatcher import dispatcher
from .config.settings import settings


def solve_challenge(
    files: list[str] | None = None,
    urls: list[str] | None = None,
    description: str = "",
    name: str = "",
    category: str = "unknown",
    host: str = "",
    port: int = 0,
) -> dict:
    """Solve a single CTF challenge."""
    file_paths = [Path(f) for f in (files or []) if Path(f).exists()]

    challenge = ChallengeInfo(
        name=name or (file_paths[0].stem if file_paths else "unnamed"),
        category=category,
        files=file_paths,
        urls=urls or [],
        description=description,
        host=host,
        port=port,
    )

    result = dispatcher.solve_with_fallback(challenge)
    return {
        "success": result.success,
        "flag": result.flag,
        "category": result.category,
        "approach": result.approach,
        "steps": result.steps,
        "errors": result.errors,
        "duration": result.duration_seconds,
    }


def solve_command(args: argparse.Namespace) -> int:
    """Handle the `ctf-solve` CLI command."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()
    console.print(Panel.fit("[bold cyan]Auto CTF Solver[/bold cyan]"))

    result = solve_challenge(
        files=args.files,
        urls=args.url,
        description=args.description or "",
        name=args.name or "",
        category=args.category or "unknown",
        host=args.host or "",
        port=args.port or 0,
    )

    table = Table(title="Solve Results")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Category", result["category"])
    table.add_row("Success", str(result["success"]))
    table.add_row("Approach", result["approach"])
    table.add_row("Duration", f"{result['duration']:.1f}s")
    if result["flag"]:
        table.add_row("Flag", f"[bold yellow]{result['flag']}[/bold yellow]")
    console.print(table)
    if result["errors"]:
        for err in result["errors"]:
            console.print(f"[red]Error:[/red] {err[:200]}")

    if args.writeup:
        console.print("\n[bold]Generating writeup...[/bold]")
        from .writeup.generator import WriteupGenerator
        generator = WriteupGenerator()
        writeup_path = generator.generate(
            challenge_name=args.name or "challenge",
            category=result["category"],
            result=result,
        )
        console.print(f"[green]Writeup saved to:[/green] {writeup_path}")

    return 0 if result["success"] else 1


def watch_command(args: argparse.Namespace) -> int:
    """Handle the `ctf-watch` CLI command."""
    from .watcher import ChallengeWatcher
    from rich.console import Console

    console = Console()
    console.print(f"[bold cyan]Watching:[/bold cyan] {args.directory}")

    watcher = ChallengeWatcher(
        watch_dir=Path(args.directory),
        auto_solve=True,
        auto_writeup=args.writeup,
    )
    watcher.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        console.print("\n[yellow]Watcher stopped.[/yellow]")
    return 0


def writeup_command(args: argparse.Namespace) -> int:
    """Handle the `ctf-writeup` CLI command."""
    from rich.console import Console
    from .writeup.generator import WriteupGenerator

    console = Console()
    generator = WriteupGenerator()
    output = generator.generate_from_solve_log(
        solve_log=Path(args.log),
        challenge_name=args.name or "challenge",
        category=args.category or "unknown",
    )
    console.print(f"[green]Writeup generated:[/green] {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ctf-solve",
        description="Auto CTF Solver - Multi-agent CTF challenge solver with auto writeup",
    )
    subparsers = parser.add_subparsers(dest="command")

    solve_parser = subparsers.add_parser("solve", help="Solve a CTF challenge")
    solve_parser.add_argument("--files", "-f", nargs="+", help="Challenge file paths")
    solve_parser.add_argument("--url", "-u", nargs="+", help="Challenge URLs")
    solve_parser.add_argument("--description", "-d", help="Challenge description")
    solve_parser.add_argument("--name", "-n", help="Challenge name")
    solve_parser.add_argument("--category", "-c", help="Force category (skip auto-detect)")
    solve_parser.add_argument("--host", help="Remote host")
    solve_parser.add_argument("--port", "-p", type=int, help="Remote port")
    solve_parser.add_argument("--writeup", "-w", action="store_true", help="Generate writeup")

    watch_parser = subparsers.add_parser("watch", help="Watch directory for new challenges")
    watch_parser.add_argument("directory", help="Directory to watch")
    watch_parser.add_argument("--writeup", "-w", action="store_true", help="Auto-generate writeups")

    writeup_parser = subparsers.add_parser("writeup", help="Generate writeup from solve log")
    writeup_parser.add_argument("log", help="Path to solve log JSON")
    writeup_parser.add_argument("--name", "-n", help="Challenge name")
    writeup_parser.add_argument("--category", "-c", help="Challenge category")

    args = parser.parse_args()
    if args.command == "solve":
        return solve_command(args)
    elif args.command == "watch":
        return watch_command(args)
    elif args.command == "writeup":
        return writeup_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
