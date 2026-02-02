"""CLI for unversion - manage prompts from the command line."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def find_prompts_file() -> Optional[Path]:
    """Find prompts file in common locations."""
    candidates = [
        Path("prompts/bundled.json"),
        Path("prompts.json"),
        Path("bundled.json"),
        Path(".prompts/bundled.json"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def cmd_list(args):
    """List all prompts."""
    from .store import init_store, list_prompts, get_store

    path = args.file or find_prompts_file()
    if not path:
        print("Error: No prompts file found. Use --file to specify path.", file=sys.stderr)
        sys.exit(1)

    init_store(str(path))
    keys = list_prompts()

    if args.filter:
        keys = [k for k in keys if k.startswith(args.filter)]

    if args.stats:
        # Group by prefix
        prefixes = {}
        for key in keys:
            prefix = key.split(".")[0] if "." in key else key
            prefixes[prefix] = prefixes.get(prefix, 0) + 1

        print(f"Total prompts: {len(keys)}")
        print(f"\nBy prefix:")
        for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1]):
            print(f"  {prefix}: {count}")
    else:
        for key in sorted(keys):
            print(key)


def cmd_view(args):
    """View a prompt."""
    from .store import init_store, get_store

    path = args.file or find_prompts_file()
    if not path:
        print("Error: No prompts file found. Use --file to specify path.", file=sys.stderr)
        sys.exit(1)

    init_store(str(path))
    store = get_store()
    prompt = store.get(args.key)

    if not prompt:
        print(f"Error: Prompt '{args.key}' not found", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== {args.key} ===")
    print(f"Source: {prompt.source}")
    print(f"Variables: {prompt.variables}")
    print(f"Notes: {prompt.notes or 'none'}")
    print(f"\n--- Text ({len(prompt.text)} chars) ---")
    print(prompt.text)
    print("---")


def cmd_search(args):
    """Search prompts."""
    from .store import init_store, get_store

    path = args.file or find_prompts_file()
    if not path:
        print("Error: No prompts file found. Use --file to specify path.", file=sys.stderr)
        sys.exit(1)

    init_store(str(path))
    store = get_store()

    query = args.query.lower()
    matches = []

    for key, prompt in store.items():
        if (
            query in key.lower()
            or query in prompt.text.lower()
            or query in prompt.notes.lower()
        ):
            matches.append(key)

    print(f"Found {len(matches)} matches for '{args.query}':")
    for key in sorted(matches):
        print(f"  {key}")


def cmd_validate(args):
    """Validate a prompts file."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    errors = []
    warnings = []

    # Check structure
    if "prompts" not in data:
        errors.append("Missing 'prompts' key")
    else:
        prompts = data["prompts"]
        for key, prompt in prompts.items():
            if "text" not in prompt:
                errors.append(f"{key}: Missing 'text' field")
            elif not prompt["text"]:
                warnings.append(f"{key}: Empty text")

            # Check variables match placeholders
            if "variables" in prompt and "text" in prompt:
                text = prompt["text"]
                for var in prompt["variables"]:
                    if "{" + var + "}" not in text:
                        warnings.append(f"{key}: Variable '{var}' not used in text")

    if errors:
        print("Errors:")
        for e in errors:
            print(f"  - {e}")

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")

    if not errors and not warnings:
        prompts_count = len(data.get("prompts", {}))
        print(f"Valid! {prompts_count} prompts found.")
    elif errors:
        sys.exit(1)


def cmd_stats(args):
    """Show usage statistics."""
    from .observer import get_top_prompts

    prompts = get_top_prompts(limit=args.limit)

    if not prompts:
        print("No usage data yet.")
        return

    print(f"\n=== Top Prompts by Usage ===\n")
    for p in prompts:
        success_rate = (
            (p["success_count"] / p["usage_count"] * 100) if p["usage_count"] > 0 else 0
        )
        print(f"{p['prompt_key']}")
        print(f"  Used: {p['usage_count']} times ({success_rate:.0f}% success)")
        print(f"  Last: {p['last_used']}")
        print(f"  Avg Latency: {p['avg_latency']:.0f}ms")
        print()


def cmd_export(args):
    """Export prompts to a new file."""
    from .store import init_store, get_store

    path = args.file or find_prompts_file()
    if not path:
        print("Error: No prompts file found. Use --file to specify path.", file=sys.stderr)
        sys.exit(1)

    init_store(str(path))
    store = get_store()

    # Build export data
    export = {
        "version": store.version,
        "prompts": {},
    }

    for key, prompt in store.items():
        if args.filter and not key.startswith(args.filter):
            continue
        export["prompts"][key] = {
            "text": prompt.text,
            "variables": prompt.variables,
            "source": prompt.source,
            "notes": prompt.notes,
        }

    # Write to output
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(export, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(export['prompts'])} prompts to {output_path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="unversion",
        description="Simple prompt versioning for AI applications",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    list_parser = subparsers.add_parser("list", help="List all prompts")
    list_parser.add_argument("--file", "-f", help="Path to prompts file")
    list_parser.add_argument("--filter", help="Filter by key prefix")
    list_parser.add_argument("--stats", "-s", action="store_true", help="Show statistics")

    # view command
    view_parser = subparsers.add_parser("view", help="View a prompt")
    view_parser.add_argument("key", help="Prompt key to view")
    view_parser.add_argument("--file", "-f", help="Path to prompts file")

    # search command
    search_parser = subparsers.add_parser("search", help="Search prompts")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--file", "-f", help="Path to prompts file")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate prompts file")
    validate_parser.add_argument("file", help="Path to prompts file")

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show usage statistics")
    stats_parser.add_argument("--limit", "-n", type=int, default=20, help="Number of prompts")

    # export command
    export_parser = subparsers.add_parser("export", help="Export prompts")
    export_parser.add_argument("output", help="Output file path")
    export_parser.add_argument("--file", "-f", help="Path to prompts file")
    export_parser.add_argument("--filter", help="Filter by key prefix")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "view":
        cmd_view(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "export":
        cmd_export(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
