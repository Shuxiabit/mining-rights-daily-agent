from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from .orchestrator import generate_brief


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a cited mining-rights daily brief.")
    parser.add_argument("prompt", help="Natural-language brief request")
    parser.add_argument(
        "--pdf-url", default="demo://pilbara-resource-report", help="Public mineral report PDF URL"
    )
    parser.add_argument("--output", help="Optional Markdown output path")
    parser.add_argument(
        "--direct", action="store_true", help="Call service layer directly (diagnostics/tests)"
    )
    return parser


async def _run() -> None:
    args = build_parser().parse_args()
    brief = await generate_brief(args.prompt, pdf_url=args.pdf_url, direct=args.direct)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(brief, encoding="utf-8")
        print(f"Wrote {output}")
    else:
        print(brief)


def main() -> None:
    load_dotenv()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
