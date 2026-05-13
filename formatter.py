import json
import csv
import io
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def as_table(result: dict) -> None:
    num     = result.get("number", {})
    summary = result.get("summary", {})
    spam    = result.get("spam") or {}
    dork    = result.get("web_dork") or {}
    comments = spam.get("details", {})

    table = Table(
        title=f"[bold cyan]Reverse Lookup — {num.get('international', num.get('e164'))}[/]",
        box=box.ROUNDED,
        show_header=False,
        min_width=60,
    )
    table.add_column("Field", style="bold", min_width=18)
    table.add_column("Value")

    valid_icon = "[green]Yes[/]" if num.get("valid") else "[red]No[/]"
    table.add_row("Valid number", valid_icon)
    table.add_row("E.164",           num.get("e164", "—"))
    table.add_row("National format", num.get("national", "—"))

    # --- Identity section ---
    name = summary.get("name")
    if name:
        table.add_row("[bold green]Name / Company[/]", f"[green]{name}[/]")

    possible = summary.get("possible_names") or []
    extras = [n for n in possible if n != name]
    if extras:
        table.add_row("Also found as", " · ".join(extras[:4]))

    _row(table, "YP Category",   summary.get("yp_category"))
    _row(table, "YP Address",    summary.get("yp_address"))
    _row(table, "BBB Rating",    summary.get("bbb_rating"))

    found_on = summary.get("found_on")
    if found_on:
        table.add_row("Found on", ", ".join(found_on[:6]))

    # --- Network section ---
    table.add_section()
    _row(table, "Carrier",           summary.get("carrier"))
    _row(table, "Line type",         summary.get("line_type"))
    _row(table, "Location",          summary.get("location"))
    _row(table, "State / Province",  summary.get("state"))
    _row(table, "Region (ISO)",      summary.get("region"))

    tz = summary.get("timezones")
    if tz:
        table.add_row("Timezone(s)", ", ".join(tz))

    # --- Spam section ---
    spam_count = summary.get("spam_reports")
    if spam_count is not None:
        table.add_section()
        color = "red" if spam_count > 5 else "yellow" if spam_count > 0 else "green"
        table.add_row("Spam reports", f"[{color}]{spam_count}[/]")

    labels = summary.get("spam_labels")
    if labels:
        table.add_row("Spam labels", ", ".join(labels))

    notes_comments = comments.get("800notes", {}).get("recent_comments")
    if notes_comments:
        for i, c in enumerate(notes_comments[:3], 1):
            table.add_row(f"Comment {i}", c[:120])

    # --- Web snippets section ---
    raw = dork.get("raw_results") or []
    if raw:
        table.add_section()
        for i, r in enumerate(raw[:4], 1):
            snippet = r.get("snippet", "")[:110]
            label   = r.get("url", f"Result {i}")[:30]
            if snippet:
                table.add_row(label, snippet)

    console.print(table)


def _row(table: Table, label: str, value) -> None:
    if value:
        table.add_row(label, str(value))


def as_json(result: dict) -> str:
    return json.dumps(result, indent=2, default=str)


def as_csv(results: list[dict]) -> str:
    if not results:
        return ""
    out = io.StringIO()
    # Flatten summary + number fields for CSV
    rows = []
    for r in results:
        flat = {**r.get("number", {}), **r.get("summary", {})}
        rows.append(flat)
    writer = csv.DictWriter(out, fieldnames=rows[0].keys(), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()
