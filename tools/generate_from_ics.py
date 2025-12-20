#!/usr/bin/env python3
"""
Generate activities schedule from Groups.io iCal feed and update activities.md

This script fetches the public iCal feed, parses events, and updates the
activities markdown file between comment markers.

Usage:
    python generate_from_ics.py [OPTIONS]
"""

import sys
import re
import requests
from datetime import datetime, date
from zoneinfo import ZoneInfo
from icalendar import Calendar
import recurring_ical_events
import click


# Event categorization based on name patterns
EVENT_CATEGORIES = {
    'member_meeting': {
        'keywords': ['bcars member meeting', 'member meeting', '#meetings'],
        'format': '[BCARS Members Meeting @ {time}](/meetings/)',
        'priority': 1,
        'skip_location': True
    },
    'dinner': {
        'keywords': ['dinner', 'holiday meeting', 'year end', 'holiday dinner'],
        'format': 'BCARS Year End Holiday Dinner, {location}',
        'priority': 1,
        'skip_location': False
    },
    'field_day': {
        'keywords': ['field day', 'winter field day'],
        'format': '**[{name}](/fieldday/)**',
        'priority': 2
    },
    've_workshop': {
        'keywords': ['ve', 'workshop', 'license session'],
        'format': '**[VE Session @{time}](/license/) and [Technician Workshop @ 11AM](/workshops/)**',
        'priority': 2
    },
    'set_exercise': {
        'keywords': ['set exercise', 'set'],
        'format': '**{name}**',
        'priority': 2
    },
    'picnic': {
        'keywords': ['picnic'],
        'format': '**BCARS Members Picnic**, {location}',
        'priority': 2
    },
}


def fetch_ical_feed(url):
    """Fetch iCal feed from URL"""
    response = requests.get(url)
    response.raise_for_status()
    return Calendar.from_ical(response.content)


def categorize_event(summary, description):
    """Determine the category of an event"""
    name = summary.lower() if summary else ''
    desc = description.lower() if description else ''
    
    # Check for special events FIRST
    for category, config in EVENT_CATEGORIES.items():
        for keyword in config['keywords']:
            if keyword in name or keyword in desc:
                return category
    
    # Skip regular nets
    if 'ares' in name or 'races' in name or 'net' in name:
        if 'member meeting' not in name and 'field day' not in name and 'set' not in name:
            return None
    
    # If it has a meaningful name, include it
    if summary and summary != 'Untitled':
        return 'other'
    
    return None


def format_time(dt):
    """Format time for display"""
    if dt.hour == 0 and dt.minute == 0:
        return ''
    return dt.strftime('%-I:%M%p')


def format_date_range(dtstart, dtend):
    """Format date or date range"""
    start_date = dtstart.date() if hasattr(dtstart, 'date') else dtstart
    end_date = dtend.date() if hasattr(dtend, 'date') else dtend
    
    # Single day event
    if start_date == end_date or (end_date - start_date).days == 0:
        return start_date.strftime('%B %-d')
    
    # Multi-day event
    if start_date.month == end_date.month:
        # Same month: "June 28-29"
        return f"{start_date.strftime('%B %-d')}-{end_date.strftime('%-d')}"
    else:
        # Different months: "June 28 - July 1"  
        return f"{start_date.strftime('%B %-d')} - {end_date.strftime('%B %-d')}"


def format_event_line(event, category):
    """Format an event as a markdown line"""
    summary = str(event.get('summary', 'Untitled'))
    location = str(event.get('location', ''))
    dtstart = event.get('dtstart').dt
    dtend = event.get('dtend').dt
    
    # Convert to datetime if date
    if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
        dtstart = datetime.combine(dtstart, datetime.min.time())
    if isinstance(dtend, date) and not isinstance(dtend, datetime):
        dtend = datetime.combine(dtend, datetime.min.time())
    
    # Ensure timezone aware
    if dtstart.tzinfo is None:
        dtstart = dtstart.replace(tzinfo=ZoneInfo('America/New_York'))
    if dtend.tzinfo is None:
        dtend = dtend.replace(tzinfo=ZoneInfo('America/New_York'))
    
    # Convert to Eastern time
    eastern = ZoneInfo('America/New_York')
    dtstart = dtstart.astimezone(eastern)
    dtend = dtend.astimezone(eastern)
    
    date_str = format_date_range(dtstart, dtend)
    time_str = format_time(dtstart)
    
    # Get category config
    if category in EVENT_CATEGORIES:
        config = EVENT_CATEGORIES[category]
        template = config['format']
        skip_location = config.get('skip_location', False)
    else:
        template = '**{name}**'
        skip_location = False
    
    # Format the line
    try:
        line = template.format(
            name=summary,
            time=time_str,
            location=location,
            url=''
        )
    except KeyError:
        line = f'**{summary}**'
        if location and not skip_location:
            line += f', {location}'
    
    # Add date prefix
    result = f'- {date_str} {line}'
    
    # Add location if not already included and not skipped
    if location and not skip_location and '{location}' not in template and location not in line:
        if len(location) > 60:
            location = location[:57] + '...'
        result += f' – {location}'
    
    return result


def parse_events_from_ical(cal, year):
    """Parse events from iCal calendar for a specific year"""
    events = []
    start_of_year = datetime(year, 1, 1, tzinfo=ZoneInfo('America/New_York'))
    end_of_year = datetime(year, 12, 31, 23, 59, 59, tzinfo=ZoneInfo('America/New_York'))
    
    # Use recurring_ical_events to expand recurring events
    expanded_events = recurring_ical_events.of(cal).between(start_of_year, end_of_year)
    
    for component in expanded_events:
        # Skip cancelled events
        status = component.get('status')
        if status and str(status).upper() == 'CANCELLED':
            continue
        
        dtstart = component.get('dtstart')
        if not dtstart:
            continue
        
        dt = dtstart.dt
        
        # Convert date to datetime for comparison
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        
        # Ensure timezone aware
        if isinstance(dt, datetime) and dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('America/New_York'))
        
        summary = str(component.get('summary', ''))
        description = str(component.get('description', ''))
        
        category = categorize_event(summary, description)
        if category:
            events.append({
                'component': component,
                'category': category,
                'dtstart': dt,
                'summary': summary
            })
    
    # Sort by date
    events.sort(key=lambda x: x['dtstart'])
    
    return events


def generate_schedule(cal, year):
    """Generate schedule markdown for a year"""
    events = parse_events_from_ical(cal, year)
    
    lines = []
    for item in events:
        line = format_event_line(item['component'], item['category'])
        lines.append(line)
    
    return '\n'.join(lines)


def update_activities_file(file_path, ical_url, current_year=None, next_year=None):
    """Update activities.md file with schedules from iCal feed"""
    now = datetime.now()
    
    if current_year is None:
        current_year = now.year
    if next_year is None:
        next_year = current_year + 1
    
    # Fetch and parse iCal feed
    click.echo(f'Fetching iCal feed from {ical_url}...', err=True)
    cal = fetch_ical_feed(ical_url)
    
    # Generate schedules starting from beginning of current month
    # through end of next year
    start_date = datetime(now.year, now.month, 1, tzinfo=ZoneInfo('America/New_York'))
    end_date = datetime(next_year, 12, 31, 23, 59, 59, tzinfo=ZoneInfo('America/New_York'))
    
    click.echo(f'Generating schedule from {start_date.strftime("%B %Y")} through {end_date.strftime("%B %Y")}...', err=True)
    
    # Get all events in the range
    events = []
    for component in recurring_ical_events.of(cal).between(start_date, end_date):
        # Skip cancelled events
        status = component.get('status')
        if status and str(status).upper() == 'CANCELLED':
            continue
        
        dtstart = component.get('dtstart')
        if not dtstart:
            continue
        
        dt = dtstart.dt
        
        # Convert date to datetime for comparison
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        
        # Ensure timezone aware
        if isinstance(dt, datetime) and dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('America/New_York'))
        
        summary = str(component.get('summary', ''))
        description = str(component.get('description', ''))
        
        category = categorize_event(summary, description)
        if category:
            events.append({
                'component': component,
                'category': category,
                'dtstart': dt,
                'summary': summary,
                'year': dt.year
            })
    
    # Sort by date
    events.sort(key=lambda x: x['dtstart'])
    
    # Group events by year
    events_by_year = {}
    for event in events:
        year = event['year']
        if year not in events_by_year:
            events_by_year[year] = []
        events_by_year[year].append(event)
    
    # Generate markdown for each year
    schedule_parts = []
    for year in sorted(events_by_year.keys()):
        year_events = events_by_year[year]
        schedule_parts.append(f'## {year} Schedule\n')
        
        for event in year_events:
            line = format_event_line(event['component'], event['category'])
            schedule_parts.append(line)
        
        schedule_parts.append('')  # Empty line between years
    
    # Add iCal subscription link at the bottom
    schedule_parts.append('---\n')
    schedule_parts.append('📅 **Subscribe to Calendar**: [Add BCARS calendar to your calendar app](' + ical_url + ')')
    schedule_parts.append('')
    schedule_parts.append('*Click the link above to subscribe in Apple Calendar, Google Calendar, Outlook, or any calendar app that supports iCal feeds. Your calendar will automatically stay in sync with updates.*')
    
    combined_schedule = '\n'.join(schedule_parts).strip()
    
    # Read existing file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update the single marked section
    pattern = r'(<!-- GENERATED-START -->)(.*?)(<!-- GENERATED-END -->)'
    replacement = f'<!-- GENERATED-START -->\n\n{combined_schedule}\n\n<!-- GENERATED-END -->'
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        years_msg = ', '.join(str(y) for y in sorted(events_by_year.keys()))
        click.echo(f'✓ Updated schedules for {years_msg}', err=True)
        click.echo(f'  Date range: {start_date.strftime("%B %Y")} - {end_date.strftime("%B %Y")}', err=True)
    else:
        click.echo(f'⚠ No markers found (<!-- GENERATED-START/END -->)', err=True)
        return False
    
    # Write updated content
    with open(file_path, 'w') as f:
        f.write(content)
    
    click.echo(f'\n✓ Updated {file_path}', err=True)
    return True


@click.command()
@click.option('--ical-url',
              default='https://groups.io/g/bcars/ics/8588710/260074914/feed.ics',
              help='iCal feed URL')
@click.option('--activities-file',
              default='content/200-activities.md',
              help='Path to activities markdown file')
@click.option('--current-year',
              type=int,
              help='Current year (defaults to this year)')
@click.option('--next-year',
              type=int,
              help='Next year (defaults to current + 1)')
@click.option('--dry-run',
              is_flag=True,
              help='Show what would be generated without updating file')
def main(ical_url, activities_file, current_year, next_year, dry_run):
    """
    Generate activities schedule from iCal feed and update activities.md
    
    This script fetches the Groups.io iCal feed and updates the schedule
    sections in activities.md between comment markers.
    
    The activities.md file should have markers like:
    
        ## 2025 Schedule
        
        <!-- GENERATED-2025-START -->
        (schedule will be inserted here)
        <!-- GENERATED-2025-END -->
    
    Examples:
    
        # Update activities.md with current and next year
        python generate_from_ics.py
        
        # Dry run to see what would be generated
        python generate_from_ics.py --dry-run
        
        # Update specific years
        python generate_from_ics.py --current-year 2025 --next-year 2026
    """
    try:
        if current_year is None:
            current_year = datetime.now().year
        if next_year is None:
            next_year = current_year + 1
        
        if dry_run:
            # Just show what would be generated
            now = datetime.now()
            
            if current_year is None:
                current_year = now.year
            if next_year is None:
                next_year = current_year + 1
            
            cal = fetch_ical_feed(ical_url)
            
            # Use sliding window: start of current month through end of next year
            start_date = datetime(now.year, now.month, 1, tzinfo=ZoneInfo('America/New_York'))
            end_date = datetime(next_year, 12, 31, 23, 59, 59, tzinfo=ZoneInfo('America/New_York'))
            
            click.echo(f'Date range: {start_date.strftime("%B %Y")} - {end_date.strftime("%B %Y")}\n', err=True)
            
            # Get all events in the range
            events = []
            for component in recurring_ical_events.of(cal).between(start_date, end_date):
                status = component.get('status')
                if status and str(status).upper() == 'CANCELLED':
                    continue
                
                dtstart = component.get('dtstart')
                if not dtstart:
                    continue
                
                dt = dtstart.dt
                if isinstance(dt, date) and not isinstance(dt, datetime):
                    dt = datetime.combine(dt, datetime.min.time())
                if isinstance(dt, datetime) and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo('America/New_York'))
                
                summary = str(component.get('summary', ''))
                description = str(component.get('description', ''))
                
                category = categorize_event(summary, description)
                if category:
                    events.append({
                        'component': component,
                        'category': category,
                        'dtstart': dt,
                        'summary': summary,
                        'year': dt.year
                    })
            
            events.sort(key=lambda x: x['dtstart'])
            
            # Group and display by year
            events_by_year = {}
            for event in events:
                year = event['year']
                if year not in events_by_year:
                    events_by_year[year] = []
                events_by_year[year].append(event)
            
            for year in sorted(events_by_year.keys()):
                click.echo(f'## {year} Schedule\n')
                for event in events_by_year[year]:
                    line = format_event_line(event['component'], event['category'])
                    click.echo(line)
                click.echo('')  # Empty line between years
            
            # Add iCal subscription link
            click.echo('---\n')
            click.echo(f'📅 **Subscribe to Calendar**: [Add BCARS calendar to your calendar app]({ical_url})')
            click.echo('')
            click.echo('*Click the link above to subscribe in Apple Calendar, Google Calendar, Outlook, or any calendar app that supports iCal feeds. Your calendar will automatically stay in sync with updates.*')
        else:
            # Update the file
            update_activities_file(activities_file, ical_url, current_year, next_year)
        
        return 0
        
    except Exception as e:
        click.echo(f'Error: {e}', err=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

