#!/usr/bin/env python3
"""Compatibility entry point; the pipeline has one implementation in scripts."""

import asyncio
import sys

from scripts import portfolio_positioning_memo as implementation


if __name__ == "__main__":
    raise SystemExit(asyncio.run(implementation._async_main(implementation._build_parser().parse_args())))
else:
    # Keep existing imports and monkeypatched callers on the same module object.
    sys.modules[__name__] = implementation
