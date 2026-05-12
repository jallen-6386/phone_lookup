#!/usr/bin/env python3
"""
phone_lookup — reverse phone number lookup CLI

Usage:
  python cli.py 5551234567
  python cli.py +44 7911 123456
  python cli.py --batch numbers.csv --format csv
  python cli.py 5551234567 --format json
  python cli.py 5551234567 --no-scrape
  python cli.py --clear-cache
"""
import sys
import argparse
import csv as csv_module

import cache
import normalizer
import aggregator
import formatter
from rich.console import Console

console = Console()


def lookup_one(raw: str, no_scrape: bool, no_cache: bool) -> dict | None:
    parsed = normalizer.parse(raw)
    if parsed is None:
        console.print(f"[red]Could not parse number:[/] {raw!r}")
        return None

    if not parsed.is_possible:
        console.print(f"[yellow]Warning:[/] {raw!r} does not look like a real number.")

    if not no_cache:
        cached = cache.get(parsed.e164)
        if cached:
            console.print(f"[dim](cached)[/]")
            return cached

    result = aggregator.run(parsed, no_scrape=no_scrape)

    if not no_cache:
        cache.put(parsed.e164, result)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="phone_lookup",
        description="Free reverse phone number lookup",
    )
    parser.add_argument(
        "number",
        nargs="*",
        help="Phone number(s) to look up (any common format)",
    )
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="CSV file with a column named 'number' for bulk lookups",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--no-scrape",
        action="store_true",
        help="Skip public caller ID scraping (faster, no spam data)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore and do not write the local cache",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached results and exit",
    )
    parser.add_argument(
        "--region",
        default="US",
        metavar="CC",
        help="Default region for numbers without a country code (default: US)",
    )

    args = parser.parse_args()

    if args.clear_cache:
        cache.clear()
        console.print("[green]Cache cleared.[/]")
        sys.exit(0)

    numbers: list[str] = list(args.number)

    if args.batch:
        try:
            with open(args.batch, newline="") as f:
                reader = csv_module.DictReader(f)
                numbers += [row["number"] for row in reader if "number" in row]
        except FileNotFoundError:
            console.print(f"[red]File not found:[/] {args.batch}")
            sys.exit(1)
        except KeyError:
            console.print("[red]Batch CSV must have a column named 'number'[/]")
            sys.exit(1)

    if not numbers:
        parser.print_help()
        sys.exit(0)

    results = []
    for raw in numbers:
        # Respect any --region default by re-parsing with it
        parsed = normalizer.parse(raw, default_region=args.region)
        if parsed is None:
            console.print(f"[red]Skipping unparseable number:[/] {raw!r}")
            continue
        if not parsed.is_possible:
            console.print(f"[yellow]Warning:[/] {raw!r} may not be a real number.")

        cached = None if args.no_cache else cache.get(parsed.e164)
        if cached:
            console.print(f"[dim](cached)[/]")
            result = cached
        else:
            result = aggregator.run(parsed, no_scrape=args.no_scrape)
            if not args.no_cache:
                cache.put(parsed.e164, result)

        results.append(result)

    if args.format == "table":
        for r in results:
            formatter.as_table(r)
    elif args.format == "json":
        if len(results) == 1:
            print(formatter.as_json(results[0]))
        else:
            import json
            print(json.dumps(results, indent=2, default=str))
    elif args.format == "csv":
        print(formatter.as_csv(results))


if __name__ == "__main__":
    main()
