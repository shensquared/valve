#!/usr/bin/env python3
"""
Verify semester JSON contains all required keys/events from keys.json.

Usage:
    python3 verify_keys.py [--semester SEMESTER|all]
"""

import argparse
import glob
import json
import os
import re
import sys


def load_json(path):
    with open(path) as f:
        return json.load(f)


def discover_semesters(semesters_dir):
    """Discover all semester JSON files (excluding keys.json)."""
    pattern = os.path.join(semesters_dir, '*.json')
    semesters = []
    for path in glob.glob(pattern):
        name = os.path.basename(path).replace('.json', '')
        if name != 'keys' and re.match(r'^(fall|spring)\d{2}$', name):
            semesters.append(name)
    return sorted(semesters)


def get_season(semester):
    """Extract season (fall/spring) from semester name."""
    if semester.startswith('fall'):
        return 'fall'
    elif semester.startswith('spring'):
        return 'spring'
    return None


def check_dates(data, required_dates):
    """Check that all required date fields exist."""
    missing = []
    for field in required_dates:
        if field not in data:
            missing.append(field)
    return missing


def check_events(events, required_names):
    """Check that required events exist (substring match)."""
    missing = []
    event_names = [e['name'].lower() for e in events]

    for req in required_names:
        req_lower = req.lower()
        found = any(req_lower in name for name in event_names)
        if not found:
            missing.append(req)

    return missing


def verify_semester(semester, json_path, keys):
    """Verify a semester JSON against keys."""
    print(f"\n{semester.upper()}")
    print("=" * 50)

    try:
        data = load_json(json_path)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return False

    all_ok = True
    season = get_season(semester)

    # Check required dates
    required_dates = keys.get('dates', {}).get('required', [])
    missing_dates = check_dates(data, required_dates)
    if missing_dates:
        print(f"Missing date fields:")
        for d in missing_dates:
            print(f"  - {d}")
        all_ok = False
    else:
        print(f"Date fields: All {len(required_dates)} present ✓")

    # Check holidays
    holidays = data.get('holidays', [])
    required_holidays = list(keys.get('holidays', {}).get('common', []))
    required_holidays.extend(keys.get('holidays', {}).get(season, []))

    if required_holidays:
        missing_holidays = check_events(holidays, required_holidays)
        if missing_holidays:
            print(f"Missing holidays:")
            for h in missing_holidays:
                print(f"  - {h}")
            all_ok = False
        else:
            print(f"Holidays: All {len(required_holidays)} required present ✓")

    return all_ok


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    semesters_dir = os.path.join(root_dir, 'semesters')
    keys_path = os.path.join(semesters_dir, 'keys.json')

    # Discover available semesters
    available = discover_semesters(semesters_dir)

    parser = argparse.ArgumentParser(description='Verify semester JSON has required keys')
    parser.add_argument(
        '--semester', '-s',
        default='all',
        help=f'Semester to verify (available: {", ".join(available)}, or "all")'
    )
    args = parser.parse_args()

    if not os.path.exists(keys_path):
        print(f"Error: keys.json not found at {keys_path}", file=sys.stderr)
        sys.exit(1)

    keys = load_json(keys_path)

    # Determine which semesters to verify
    if args.semester == 'all':
        semesters = available
    elif args.semester in available:
        semesters = [args.semester]
    else:
        print(f"Error: Unknown semester '{args.semester}'", file=sys.stderr)
        print(f"Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    if not semesters:
        print("No semester files found in semesters/", file=sys.stderr)
        sys.exit(1)

    all_ok = True
    for sem in semesters:
        json_path = os.path.join(semesters_dir, f'{sem}.json')
        ok = verify_semester(sem, json_path, keys)
        all_ok = all_ok and ok

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    if all_ok:
        print("All required keys present!")
    else:
        print("Missing keys found - check above")

    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
