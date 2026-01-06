#!/usr/bin/env python3
"""
Verify semester JSON class day counts against MIT Registrar official counts.

Source: https://registrar.mit.edu/calendar/class-days

Usage:
    python3 verify_classdays.py [--semester SEMESTER|all]
"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta

WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']


def load_json(path):
    """Load a JSON file."""
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


def count_class_days(start_date, end_date, holidays):
    """Count class days by weekday, excluding holidays.

    Also handles schedule substitutions (e.g., "Monday schedule" on a Tuesday).
    Returns dict with counts per weekday and total.
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    # Find schedule substitutions from holidays
    # e.g., "Monday Schedule Shift" or "Monday schedule of classes"
    substitutions = {}  # date -> substitute_weekday

    for h in holidays:
        name_lower = h['name'].lower()
        if 'schedule' in name_lower and ('shift' in name_lower or 'classes' in name_lower or 'held' in name_lower):
            for day in WEEKDAYS:
                if day.lower() in name_lower:
                    substitutions[h['date']] = day
                    break

    # Build set of holiday dates (excluding schedule shifts)
    holiday_dates = set(h['date'] for h in holidays if h['date'] not in substitutions)

    counts = {day: 0 for day in WEEKDAYS}
    total = 0
    current = start

    while current <= end:
        weekday = current.strftime('%A')
        date_str = current.strftime('%Y-%m-%d')

        if weekday in WEEKDAYS and date_str not in holiday_dates:
            # Check for schedule substitution
            if date_str in substitutions:
                counts[substitutions[date_str]] += 1
            else:
                counts[weekday] += 1
            total += 1

        current += timedelta(days=1)

    counts['total'] = total
    return counts, holiday_dates, substitutions


def check_required_dates(data, keys):
    """Check that all required date fields exist."""
    required = keys.get('dates', {}).get('required', [])
    missing = [f for f in required if f not in data]
    return missing


def check_required_holidays(data, keys, season):
    """Check that all required holidays exist."""
    holidays = data.get('holidays', [])
    holiday_names = [h['name'].lower() for h in holidays]

    required = list(keys.get('holidays', {}).get('common', []))
    required.extend(keys.get('holidays', {}).get(season, []))

    missing = []
    for req in required:
        req_lower = req.lower()
        if not any(req_lower in name for name in holiday_names):
            missing.append(req)

    return missing


def verify_semester(semester, json_path, keys):
    """Verify class day counts for a semester."""
    print(f"\n{semester.upper()}")
    print("=" * 50)

    try:
        data = load_json(json_path)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return False

    season = get_season(semester)
    all_ok = True

    # Check required dates from keys
    missing_dates = check_required_dates(data, keys)
    if missing_dates:
        print(f"Missing required dates: {missing_dates}")
        all_ok = False

    # Check required holidays
    missing_holidays = check_required_holidays(data, keys, season)
    if missing_holidays:
        print(f"Missing required holidays: {missing_holidays}")
        all_ok = False

    # Get dates from semester JSON
    start_date = data.get('startDate')
    end_date = data.get('lastClassDate')

    if not start_date or not end_date:
        print("Error: startDate or lastClassDate not found")
        return False

    holidays = data.get('holidays', [])

    # Count class days
    counts, holiday_dates, substitutions = count_class_days(start_date, end_date, holidays)

    print(f"Period: {start_date} to {end_date}")
    print(f"Holidays: {len(holidays)}")
    if substitutions:
        print(f"Schedule substitutions: {len(substitutions)}")
        for date, sub_day in sorted(substitutions.items()):
            actual_day = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
            print(f"  {date} ({actual_day}) -> {sub_day} schedule")
    print()

    # Get official counts from keys.json
    official = keys.get('officialClassDays', {}).get(semester)

    if not official:
        print(f"No official counts for {semester} - showing computed only")
        print(f"{'Day':<12} {'Computed':>8}")
        print("-" * 22)
        for day in WEEKDAYS:
            print(f"{day:<12} {counts[day]:>8}")
        print("-" * 22)
        print(f"{'TOTAL':<12} {counts['total']:>8}")
    else:
        # Compare counts
        print(f"{'Day':<12} {'Official':>8} {'Computed':>8} {'Diff':>6}")
        print("-" * 36)

        for day in WEEKDAYS:
            off = official[day]
            comp = counts[day]
            diff = comp - off

            if diff != 0:
                all_ok = False
                marker = f" {'↑' if diff > 0 else '↓'}"
                print(f"{day:<12} {off:>8} {comp:>8} {diff:>+6}{marker}")
            else:
                print(f"{day:<12} {off:>8} {comp:>8} {'':>6} ✓")

        print("-" * 36)
        off_total = official['total']
        comp_total = counts['total']
        diff_total = comp_total - off_total

        if diff_total != 0:
            all_ok = False
            print(f"{'TOTAL':<12} {off_total:>8} {comp_total:>8} {diff_total:>+6}")
        else:
            print(f"{'TOTAL':<12} {off_total:>8} {comp_total:>8} {'':>6} ✓")

    # Show holidays in period
    print(f"\nHolidays in period:")
    period_holidays = []
    for h in sorted(holidays, key=lambda x: x['date']):
        if start_date <= h['date'] <= end_date:
            d = datetime.strptime(h['date'], '%Y-%m-%d')
            weekday = d.strftime('%A')
            print(f"  {h['date']} ({weekday[:3]}): {h['name']}")
            period_holidays.append(h)

    # Detect potential issues with begins/ends holidays
    if not all_ok:
        begins = [h for h in period_holidays if 'start' in h['name'].lower() or 'begin' in h['name'].lower()]
        ends = [h for h in period_holidays if 'end' in h['name'].lower()]

        if begins and ends:
            print(f"\nNOTE: Found 'start/end' holidays - check if middle days are included")

    return all_ok


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    semesters_dir = os.path.join(script_dir, 'semesters')
    keys_path = os.path.join(semesters_dir, 'keys.json')

    # Discover available semesters
    available = discover_semesters(semesters_dir)

    parser = argparse.ArgumentParser(
        description='Verify class day counts against MIT Registrar'
    )
    parser.add_argument(
        '--semester', '-s',
        default='all',
        help=f'Semester to verify (available: {", ".join(available)}, or "all")'
    )
    args = parser.parse_args()

    # Load keys
    if os.path.exists(keys_path):
        keys = load_json(keys_path)
    else:
        print(f"Warning: keys.json not found at {keys_path}", file=sys.stderr)
        keys = {}

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
        print("All verifications passed!")
    else:
        print("Discrepancies found - check above")

    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
