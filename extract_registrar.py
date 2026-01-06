#!/usr/bin/env python3
"""
Extract MIT Registrar calendar dates and generate semester JSON configs.

Usage:
    python3 extract_registrar.py [--semester fall25|spring26]

Fetches https://registrar.mit.edu/calendar and extracts holidays (no classes).
"""

import argparse
import json
import re
import sys
from datetime import datetime
from urllib.request import urlopen, Request
from html.parser import HTMLParser


class RegistrarCalendarParser(HTMLParser):
    """Parse MIT registrar calendar HTML to extract events."""

    def __init__(self):
        super().__init__()
        self.events = []
        self.current_date = None
        self.current_text = []
        self.in_event_item = False
        self.in_date = False
        self.in_details = False
        self.capture_text = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get('class', '')

        # Event item container
        if 'calendar-item' in classes or 'event-item' in classes:
            self.in_event_item = True
            self.current_date = None
            self.current_text = []

        # Date element
        if tag == 'time' and 'datetime' in attrs_dict:
            self.current_date = attrs_dict['datetime'][:10]  # YYYY-MM-DD

        # Event description
        if self.in_event_item and tag in ('p', 'span', 'div'):
            if 'event-description' in classes or 'calendar-description' in classes:
                self.capture_text = True

    def handle_endtag(self, tag):
        if tag in ('p', 'span', 'div') and self.capture_text:
            self.capture_text = False

        if tag in ('div', 'li', 'article') and self.in_event_item:
            if self.current_date and self.current_text:
                text = ' '.join(self.current_text).strip()
                if text:
                    self.events.append({
                        'date': self.current_date,
                        'name': text
                    })
            self.in_event_item = False
            self.current_date = None
            self.current_text = []

    def handle_data(self, data):
        if self.capture_text or self.in_event_item:
            text = data.strip()
            if text:
                self.current_text.append(text)


def fetch_registrar_calendar():
    """Fetch the MIT registrar calendar page."""
    url = 'https://registrar.mit.edu/calendar'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as response:
        return response.read().decode('utf-8')


def extract_events_from_html(html):
    """Extract calendar events from HTML using regex patterns."""
    events = []

    # Pattern for dates in format: Month Day, Year or Month Day
    # Look for calendar entries with dates and descriptions

    # Find month sections and their events
    month_pattern = r'<h[23][^>]*>([A-Z][a-z]+ \d{4})</h[23]>'
    event_pattern = r'<(?:div|li|p)[^>]*class="[^"]*(?:calendar|event)[^"]*"[^>]*>.*?</(?:div|li|p)>'

    # Alternative: Look for date-event pairs in various formats
    # Pattern: "Mon, Sep 2" or "September 2" followed by event text
    date_event_pattern = r'(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+)?([A-Z][a-z]{2,8})\s+(\d{1,2})(?:,?\s+(\d{4}))?\s*[-–]?\s*([^<\n]+)'

    matches = re.findall(date_event_pattern, html)

    current_year = datetime.now().year
    month_map = {
        'Jan': 1, 'January': 1, 'Feb': 2, 'February': 2,
        'Mar': 3, 'March': 3, 'Apr': 4, 'April': 4,
        'May': 5, 'Jun': 6, 'June': 6, 'Jul': 7, 'July': 7,
        'Aug': 8, 'August': 8, 'Sep': 9, 'September': 9,
        'Oct': 10, 'October': 10, 'Nov': 11, 'November': 11,
        'Dec': 12, 'December': 12
    }

    for match in matches:
        month_str, day, year, text = match
        if month_str in month_map:
            month = month_map[month_str]
            year = int(year) if year else current_year
            try:
                date = datetime(year, month, int(day))
                events.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'name': text.strip()
                })
            except ValueError:
                pass

    return events


def extract_events_simple(html):
    """Extract events from MIT registrar calendar HTML table structure.

    The HTML structure is:
    <tr>
      <td class="1"><div id="calendar-link-YYYY-MM-DD">Mon D</div></td>
      <td class="2">Day of week</td>
      <td>
        <p>Event description</p>
        <p>Another event</p>
      </td>
    </tr>
    """
    events = []

    # Find all calendar-link dates and their associated events
    # Pattern: find the date div, then capture all <p> content until next row
    pattern = r'<div\s+id="calendar-link-(\d{4}-\d{2}-\d{2})"[^>]*>[^<]*</div>.*?</td>.*?<td[^>]*>.*?</td>.*?<td[^>]*>(.*?)</(?:td|tr)>'

    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

    for date, content in matches:
        # Extract all <p> content from the event cell
        p_pattern = r'<p[^>]*>(.*?)</p>'
        p_matches = re.findall(p_pattern, content, re.DOTALL)

        for p_content in p_matches:
            # Clean up the text - remove HTML tags, normalize whitespace
            text = re.sub(r'<[^>]+>', '', p_content)  # Remove HTML tags
            # Decode HTML entities
            text = re.sub(r'&amp;', '&', text)
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'&#039;', "'", text)
            text = re.sub(r'&mdash;', '—', text)
            text = re.sub(r'&ndash;', '–', text)
            text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace

            if text and len(text) > 2:
                events.append({'date': date, 'name': text})

    return events


def clean_event_name(name):
    """Clean up event name for display."""
    # Remove common suffixes
    name = re.sub(r'\s*[—–-]\s*(holiday|no classes?)\.?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*[—–-]\s*fall term\.?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*[—–-]\s*spring term\.?$', '', name, flags=re.IGNORECASE)
    # Remove trailing periods
    name = name.rstrip('.')
    return name.strip()


def is_holiday(name):
    """Check if an event is a holiday (no classes)."""
    name_lower = name.lower()

    holiday_keywords = [
        'no class', 'holiday', 'labor day', 'columbus',
        'indigenous peoples', 'veterans day', 'thanksgiving',
        'mlk', 'martin luther king', 'presidents', "president's",
        'patriots', 'memorial day', 'spring break', 'winter break',
        'spring vacation', 'winter vacation', 'institute holiday',
        'juneteenth', 'independence day'
    ]

    for keyword in holiday_keywords:
        if keyword in name_lower:
            return True

    return False


def filter_events_for_semester(events, semester):
    """Filter events to a specific semester date range."""
    if semester == 'fall25':
        start = datetime(2025, 8, 1)
        end = datetime(2025, 12, 31)
    elif semester == 'spring26':
        start = datetime(2026, 1, 1)
        end = datetime(2026, 6, 30)
    elif semester == 'fall26':
        start = datetime(2026, 8, 1)
        end = datetime(2026, 12, 31)
    else:
        return events  # Return all if unknown semester

    filtered = []
    for event in events:
        try:
            date = datetime.strptime(event['date'], '%Y-%m-%d')
            if start <= date <= end:
                filtered.append(event)
        except ValueError:
            pass

    return filtered


def create_semester_config(events, semester):
    """Create a semester config JSON from extracted events."""
    holidays = []

    # Deduplicate events by date+name
    seen = set()
    for event in events:
        # Clean the name before storing
        cleaned_name = clean_event_name(event['name'])
        key = (event['date'], cleaned_name)
        if key in seen:
            continue
        seen.add(key)

        # Only include holidays (no classes)
        if is_holiday(event['name']):
            entry = {'date': event['date'], 'name': cleaned_name}
            holidays.append(entry)

    # Sort by date
    holidays.sort(key=lambda x: x['date'])

    # Determine semester dates
    if semester.startswith('fall'):
        year = int('20' + semester[4:6])
        config = {
            'name': f'Fall {year}',
            'firstMonday': f'{year}-09-01',       # Monday of first week (often Labor Day)
            'startDate': f'{year}-09-03',         # First day of classes
            'addDate': f'{year}-10-03',           # Add date
            'dropDate': f'{year}-11-19',          # Drop date
            'lastDueHasFinal': f'{year}-12-05',   # Last due date (subjects with final)
            'lastDueNoFinal': f'{year}-12-05',    # Last due date (subjects without final)
            'lastClassDate': f'{year}-12-10',     # Last day of classes
            'finalPeriodStart': f'{year}-12-15',  # Final exam period start
            'finalPeriodEnd': f'{year}-12-19',    # Final exam period end
        }
    else:  # spring
        year = int('20' + semester[6:8])
        config = {
            'name': f'Spring {year}',
            'firstMonday': f'{year}-02-02',       # Monday of first week
            'startDate': f'{year}-02-02',         # First day of classes
            'addDate': f'{year}-03-06',           # Add date
            'dropDate': f'{year}-04-21',          # Drop date
            'lastDueHasFinal': f'{year}-05-08',   # Last due date (subjects with final)
            'lastDueNoFinal': f'{year}-05-08',    # Last due date (subjects without final)
            'lastClassDate': f'{year}-05-12',     # Last day of classes
            'finalPeriodStart': f'{year}-05-15',  # Final exam period start
            'finalPeriodEnd': f'{year}-05-20',    # Final exam period end
        }

    config.update({
        'holidays': holidays,
        'rowTypes': [
            {'id': 'event', 'label': 'Events/Notes', 'color': '#fff9c4'},
            {'id': 'lecture', 'label': 'Lecture', 'color': '#e3f2fd'},
            {'id': 'lectureTopic', 'label': 'Lecture Topic', 'color': '#bbdefb'},
            {'id': 'lab', 'label': 'Lab', 'color': '#e8f5e9'},
            {'id': 'staff', 'label': 'Staff', 'color': '#f3e5f5'}
        ]
    })

    return config


def main():
    parser = argparse.ArgumentParser(description='Extract MIT Registrar calendar dates')
    parser.add_argument('--semester', choices=['fall25', 'spring26', 'fall26'],
                        help='Semester to extract (default: extract all)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--raw', action='store_true', help='Output raw extracted events')
    parser.add_argument('--update', action='store_true',
                        help='Update semesters/*.json files directly')
    args = parser.parse_args()

    print('Fetching MIT Registrar calendar...', file=sys.stderr)

    try:
        html = fetch_registrar_calendar()
    except Exception as e:
        print(f'Error fetching calendar: {e}', file=sys.stderr)
        sys.exit(1)

    print(f'Fetched {len(html)} bytes', file=sys.stderr)

    # Try multiple extraction methods
    events = extract_events_simple(html)
    if not events:
        events = extract_events_from_html(html)

    print(f'Extracted {len(events)} events', file=sys.stderr)

    if args.update:
        # Update semester files directly
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        semesters_dir = os.path.join(script_dir, 'semesters')
        os.makedirs(semesters_dir, exist_ok=True)

        semesters_to_update = [args.semester] if args.semester else ['fall25', 'spring26']

        for sem in semesters_to_update:
            filtered = filter_events_for_semester(events, sem)
            print(f'{sem}: {len(filtered)} events', file=sys.stderr)
            config = create_semester_config(filtered, sem)
            output_path = os.path.join(semesters_dir, f'{sem}.json')
            with open(output_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f'Written to {output_path}', file=sys.stderr)
        return

    if args.raw:
        # Output raw events
        output = events
    elif args.semester:
        # Filter and create config for specific semester
        filtered = filter_events_for_semester(events, args.semester)
        print(f'Filtered to {len(filtered)} events for {args.semester}', file=sys.stderr)
        output = create_semester_config(filtered, args.semester)
    else:
        # Output all events grouped by category
        output = {
            'extracted_at': datetime.now().isoformat(),
            'events': events
        }

    json_output = json.dumps(output, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        print(f'Written to {args.output}', file=sys.stderr)
    else:
        print(json_output)


if __name__ == '__main__':
    main()
