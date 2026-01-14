#!/usr/bin/env python3
"""
Pre-commit hook to update the LAST_UPDATED constant in app.js
with the current date.
"""

import re
from datetime import datetime
from pathlib import Path


def main():
    app_js = Path("app.js")

    if not app_js.exists():
        print("Error: app.js not found")
        return 1

    # Get current date in the format: Jan 14, 2026
    current_date = datetime.now().strftime("%b %-d, %Y")

    # Read the file
    content = app_js.read_text()

    # Replace the LAST_UPDATED constant
    new_content = re.sub(
        r"const LAST_UPDATED = '.*?';  // Replaced by.*$",
        f"const LAST_UPDATED = '{current_date}';  // Replaced by git hook",
        content,
        flags=re.MULTILINE
    )

    # Write back if changed
    if new_content != content:
        app_js.write_text(new_content)
        print(f"Updated LAST_UPDATED to: {current_date}")
        # Stage the modified file
        import subprocess
        subprocess.run(["git", "add", "app.js"], check=True)

    return 0


if __name__ == "__main__":
    exit(main())
