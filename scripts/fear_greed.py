#!/usr/bin/env python3
"""Display CNN Fear & Greed Index."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.fear_greed import fetch_fear_greed, format_fear_greed_message


def main():
    print("=" * 50)
    print("CNN FEAR & GREED INDEX")
    print("=" * 50)
    print()

    data = fetch_fear_greed()
    if data is None:
        print("Failed to fetch Fear & Greed Index.")
        sys.exit(1)

    print(format_fear_greed_message(data))


if __name__ == "__main__":
    main()
