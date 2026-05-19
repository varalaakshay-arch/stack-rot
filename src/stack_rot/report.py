"""Render scan findings to the terminal using rich.

Output format (from the v0.1 plan):

    📦 stack-rot v0.1 — scanning ./package.json

    🪦 ABANDONED (3 packages):
      ❌ moment ^2.29.4
         → Maintenance mode since 2020.
         → Migrate to: dayjs, date-fns
         → Evidence: momentjs.com/docs/...

    ✅ HEALTHY (14 packages)

    ────────────────────
    📊 Project health: 6/10
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.text import Text

from stack_rot.scanner import Finding


# Bucket order matters: most severe first.
_BUCKETS = [
    ("dead", "ABANDONED", "🪦", "red"),
    ("deprecated", "DEPRECATED", "⚠️ ", "yellow"),
    ("stale", "STALE", "🕸️ ", "yellow"),
    ("unknown", "UNKNOWN", "❓", "dim"),
]


def render(
    manifest_path: Path,
    findings: list[Finding],
    console: Console | None = None,
) -> None:
    """Print a human-readable report for the given findings."""
    console = console or Console()

    console.print()
    console.print(
        Text.assemble(
            ("📦 stack-rot ", "bold cyan"),
            ("v0.1", "dim"),
            (" — scanning ", "white"),
            (str(manifest_path), "bold"),
        )
    )
    console.print()

    grouped = _group(findings)
    healthy_count = len(grouped.get("healthy", []))

    rendered_any_problem = False
    for status, label, emoji, color in _BUCKETS:
        items = grouped.get(status, [])
        if not items:
            continue
        rendered_any_problem = True
        _render_bucket(console, label, emoji, color, items)

    if not rendered_any_problem:
        console.print("[green]✅ No abandoned or deprecated dependencies found.[/green]")
        console.print()

    if healthy_count:
        word = "package" if healthy_count == 1 else "packages"
        console.print(f"[green]✅ HEALTHY ({healthy_count} {word})[/green]")
        console.print()

    _render_footer(console, findings)


def _group(findings: list[Finding]) -> dict[str, list[Finding]]:
    out: dict[str, list[Finding]] = {}
    for f in findings:
        out.setdefault(f.status, []).append(f)
    return out


def _render_bucket(
    console: Console,
    label: str,
    emoji: str,
    color: str,
    items: list[Finding],
) -> None:
    word = "package" if len(items) == 1 else "packages"
    console.print(f"[bold {color}]{emoji} {label} ({len(items)} {word}):[/bold {color}]")
    for f in items:
        console.print(
            f"  [bold {color}]❌ {f.dependency.name}[/bold {color}] [dim]{f.dependency.version_spec}[/dim]"
        )
        if f.reason:
            console.print(f"     [white]→ {f.reason}[/white]")
        if f.alternatives:
            alt_list = ", ".join(f.alternatives)
            console.print(f"     [green]→ Migrate to:[/green] {alt_list}")
        if f.evidence:
            console.print(f"     [dim]→ Evidence: {f.evidence}[/dim]")
        console.print()


def _render_footer(console: Console, findings: list[Finding]) -> None:
    total = len(findings)
    if total == 0:
        return

    healthy = sum(1 for f in findings if f.status == "healthy")
    score = round(10 * healthy / total)

    console.print("─" * 40)
    color = "green" if score >= 8 else "yellow" if score >= 5 else "red"
    console.print(f"[bold]📊 Project health:[/bold] [{color}]{score}/10[/{color}]")
    console.print(f"[dim]   {healthy}/{total} dependencies are healthy.[/dim]")
    console.print()