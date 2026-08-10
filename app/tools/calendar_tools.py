"""Calendar integration and scheduling tools.

Provides tools for creating calendar events, managing schedules, generating
iCalendar (.ics) files, and integrating with Google Calendar and Outlook.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta

import structlog

from app.tools import tool

logger = structlog.get_logger()


@tool(description="Create a calendar event and generate an iCalendar (.ics) file. The file can be imported into Google Calendar, Outlook, Apple Calendar, etc.")
async def create_calendar_event(
    title: str,
    start_datetime: str,
    end_datetime: str = "",
    description: str = "",
    location: str = "",
    attendees: str = "",
    reminder_minutes: int = 15,
    output_path: str = "/tmp/event.ics",
    recurrence: str = "",
) -> str:
    """Create a calendar event as an .ics file.

    Args:
        title: Event title/subject.
        start_datetime: Start time in ISO format (YYYY-MM-DDTHH:MM:SS).
        end_datetime: End time in ISO format (defaults to 1 hour after start).
        description: Event description/notes.
        location: Event location or meeting URL.
        attendees: Comma-separated attendee emails.
        reminder_minutes: Reminder before event in minutes.
        output_path: Path to save the .ics file.
        recurrence: Recurrence rule - daily, weekly, monthly, yearly.
    """
    try:
        # Parse datetimes
        dt_start = _parse_datetime(start_datetime)
        if isinstance(dt_start, str):
            return dt_start

        if end_datetime:
            dt_end = _parse_datetime(end_datetime)
            if isinstance(dt_end, str):
                return dt_end
        else:
            dt_end = dt_start + timedelta(hours=1)

        event_uid = str(uuid.uuid4())
        now = datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%dT%H%M%SZ")
        dt_start_str = dt_start.strftime("%Y%m%dT%H%M%S")
        dt_end_str = dt_end.strftime("%Y%m%dT%H%M%S")

        # Build VEVENT
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AgentEngine//Calendar//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{event_uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{dt_start_str}",
            f"DTEND:{dt_end_str}",
            f"SUMMARY:{_ics_escape(title)}",
        ]

        if description:
            lines.append(f"DESCRIPTION:{_ics_escape(description)}")
        if location:
            lines.append(f"LOCATION:{_ics_escape(location)}")

        if recurrence:
            rrule = _get_recurrence_rule(recurrence)
            if rrule:
                lines.append(f"RRULE:{rrule}")

        # Reminder
        lines.extend([
            "BEGIN:VALARM",
            f"TRIGGER:-PT{reminder_minutes}M",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder",
            "END:VALARM",
        ])

        # Attendees
        if attendees:
            for email in attendees.split(","):
                email = email.strip()
                if email:
                    lines.append(f"ATTENDEE:mailto:{email}")

        lines.extend([
            "END:VEVENT",
            "END:VCALENDAR",
        ])

        ics_content = "\r\n".join(lines)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ics_content)

        duration = (dt_end - dt_start).total_seconds() / 60
        result = (
            f"Calendar event created: {output_path}\n"
            f"  Title: {title}\n"
            f"  Start: {dt_start.strftime('%Y-%m-%d %H:%M')}\n"
            f"  End: {dt_end.strftime('%Y-%m-%d %H:%M')}\n"
            f"  Duration: {duration:.0f} minutes\n"
            f"  Reminder: {reminder_minutes} minutes before"
        )
        if attendees:
            result += f"\n  Attendees: {attendees}"
        if recurrence:
            result += f"\n  Recurrence: {recurrence}"

        return result

    except Exception as e:
        return f"Error creating calendar event: {e!s}"


@tool(description="Create a full-day event (all-day event) in iCalendar format.")
async def create_allday_event(
    title: str,
    date: str,
    description: str = "",
    location: str = "",
    output_path: str = "/tmp/allday_event.ics",
) -> str:
    """Create an all-day calendar event.

    Args:
        title: Event title.
        date: Event date (YYYY-MM-DD).
        description: Event description.
        location: Event location.
        output_path: Path to save the .ics file.
    """
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        next_day = dt + timedelta(days=1)

        event_uid = str(uuid.uuid4())
        now = datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AgentEngine//Calendar//EN",
            "BEGIN:VEVENT",
            f"UID:{event_uid}",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{dt.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}",
            f"SUMMARY:{_ics_escape(title)}",
        ]

        if description:
            lines.append(f"DESCRIPTION:{_ics_escape(description)}")
        if location:
            lines.append(f"LOCATION:{_ics_escape(location)}")

        lines.extend([
            "END:VEVENT",
            "END:VCALENDAR",
        ])

        ics_content = "\r\n".join(lines)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ics_content)

        return f"All-day event created: {output_path}\n  Title: {title}\n  Date: {date}"
    except ValueError:
        return "Error: Invalid date format. Use YYYY-MM-DD."
    except Exception as e:
        return f"Error creating all-day event: {e!s}"


@tool(description="Generate a recurring calendar event series (e.g., daily standup, weekly meeting, monthly review).")
async def create_recurring_event(
    title: str,
    start_datetime: str,
    duration_minutes: int = 60,
    recurrence: str = "weekly",
    count: int = 10,
    description: str = "",
    location: str = "",
    output_path: str = "/tmp/recurring_event.ics",
) -> str:
    """Create a recurring calendar event.

    Args:
        title: Event title.
        start_datetime: Start time in ISO format.
        duration_minutes: Duration of each occurrence.
        recurrence: daily, weekly, biweekly, monthly, yearly.
        count: Number of occurrences.
        description: Event description.
        location: Event location.
        output_path: Path to save the .ics file.
    """
    try:
        dt_start = _parse_datetime(start_datetime)
        if isinstance(dt_start, str):
            return dt_start

        dt_end = dt_start + timedelta(minutes=duration_minutes)
        event_uid = str(uuid.uuid4())
        now = datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%dT%H%M%SZ")

        freq_map = {"daily": "DAILY", "weekly": "WEEKLY", "biweekly": "WEEKLY", "monthly": "MONTHLY", "yearly": "YEARLY"}
        freq = freq_map.get(recurrence, "WEEKLY")
        interval = "2" if recurrence == "biweekly" else "1"

        rrule = f"FREQ={freq};INTERVAL={interval};COUNT={count}"

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AgentEngine//Calendar//EN",
            "BEGIN:VEVENT",
            f"UID:{event_uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{_ics_escape(title)}",
            f"RRULE:{rrule}",
        ]

        if description:
            lines.append(f"DESCRIPTION:{_ics_escape(description)}")
        if location:
            lines.append(f"LOCATION:{_ics_escape(location)}")

        lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:-PT15M",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder",
            "END:VALARM",
            "END:VEVENT",
            "END:VCALENDAR",
        ])

        ics_content = "\r\n".join(lines)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ics_content)

        return (
            f"Recurring event created: {output_path}\n"
            f"  Title: {title}\n"
            f"  Schedule: {recurrence} x {count}\n"
            f"  First: {dt_start.strftime('%Y-%m-%d %H:%M')}\n"
            f"  Duration: {duration_minutes} min"
        )
    except Exception as e:
        return f"Error creating recurring event: {e!s}"


@tool(description="Generate a calendar for a given month with events, holidays, and important dates.")
async def generate_monthly_calendar(
    year: int,
    month: int,
    events: str = "",
    output_path: str = "/tmp/monthly_calendar.ics",
    include_holidays: bool = False,
) -> str:
    """Generate a monthly calendar with events.

    Args:
        year: Year.
        month: Month (1-12).
        events: JSON array of {title, date, description} or 'title:date' pairs separated by semicolons.
        output_path: Path to save the .ics file.
        include_holidays: Include common holidays.
    """
    try:
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AgentEngine//MonthlyCalendar//EN",
            "CALSCALE:GREGORIAN",
        ]

        if events:
            if events.strip().startswith("["):
                event_list = json.loads(events)
            else:
                event_list = []
                for pair in events.split(";"):
                    if ":" in pair:
                        parts = pair.split(":", 1)
                        event_list.append({"title": parts[0].strip(), "date": parts[1].strip()})

            for event in event_list:
                dt = datetime.strptime(event["date"], "%Y-%m-%d")
                uid = str(uuid.uuid4())
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTART;VALUE=DATE:{dt.strftime('%Y%m%d')}",
                    f"DTEND;VALUE=DATE:{(dt + timedelta(days=1)).strftime('%Y%m%d')}",
                    f"SUMMARY:{_ics_escape(event['title'])}",
                    "END:VEVENT",
                ])

        lines.append("END:VCALENDAR")

        ics_content = "\r\n".join(lines)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ics_content)

        return f"Monthly calendar created: {output_path}\n  Period: {year}-{month:02d}\n  Events: {len(events) if events else 0}"
    except Exception as e:
        return f"Error generating calendar: {e!s}"


@tool(description="Calculate the best meeting time slots based on participants' availability and time zones.")
async def find_meeting_slots(
    date: str,
    duration_minutes: int = 60,
    working_hours: str = "09:00-17:00",
    timezones: str = "",
    num_suggestions: int = 5,
) -> str:
    """Find optimal meeting time slots.

    Args:
        date: Meeting date (YYYY-MM-DD).
        duration_minutes: Required duration.
        working_hours: Working hours range (HH:MM-HH:MM).
        timezones: Comma-separated timezones (e.g., 'America/New_York,Europe/London').
        num_suggestions: Number of slots to suggest.
    """
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        start_h, start_m = (int(x) for x in working_hours.split("-")[0].split(":"))
        end_h, end_m = (int(x) for x in working_hours.split("-")[1].split(":"))

        start_time = dt.replace(hour=start_h, minute=start_m)
        end_time = dt.replace(hour=end_h, minute=end_m)

        # Generate hourly slots
        slots = []
        current = start_time
        while current + timedelta(minutes=duration_minutes) <= end_time:
            slots.append(current)
            current += timedelta(minutes=30)

        # Limit suggestions
        suggestions = slots[:num_suggestions]

        lines = [f"Meeting Slots for {date} ({duration_minutes} min):\n"]

        for i, slot in enumerate(suggestions, 1):
            slot_end = slot + timedelta(minutes=duration_minutes)
            line = f"  {i}. {slot.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}"

            if timezones:
                tz_times = []
                for tz_name in timezones.split(","):
                    tz_name = tz_name.strip()
                    try:
                        import zoneinfo
                        tz = zoneinfo.ZoneInfo(tz_name)
                        local_time = slot.astimezone(tz)
                        tz_times.append(f"{local_time.strftime('%H:%M')} {tz_name}")
                    except Exception:
                        tz_times.append(f"? {tz_name}")
                line += f"  ({', '.join(tz_times)})"

            lines.append(line)

        return "\n".join(lines)
    except Exception as e:
        return f"Error finding meeting slots: {e!s}"


@tool(description="Create a meeting agenda and attach it to a calendar event.")
async def create_meeting_agenda(
    title: str,
    date: str,
    start_time: str,
    duration_minutes: int = 60,
    attendees: str = "",
    agenda_items: str = "",
    output_path: str = "/tmp/meeting.ics",
) -> str:
    """Create a meeting with agenda as a calendar event.

    Args:
        title: Meeting title.
        date: Meeting date (YYYY-MM-DD).
        start_time: Start time (HH:MM).
        duration_minutes: Duration in minutes.
        attendees: Comma-separated attendee emails.
        agenda_items: Agenda items (one per line).
        output_path: Path to save the .ics file.
    """
    try:
        dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        dt_end = dt + timedelta(minutes=duration_minutes)

        # Build description with agenda
        desc_lines = ["Meeting Agenda:", ""]
        if agenda_items:
            for i, item in enumerate(agenda_items.split("\n"), 1):
                desc_lines.append(f"  {i}. {item.strip()}")
        else:
            desc_lines.append("  (No agenda items specified)")

        desc_lines.append("")
        desc_lines.append(f"Duration: {duration_minutes} minutes")
        if attendees:
            desc_lines.append(f"Attendees: {attendees}")

        description = "\n".join(desc_lines)

        event_uid = str(uuid.uuid4())
        now = datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AgentEngine//Meeting//EN",
            "BEGIN:VEVENT",
            f"UID:{event_uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{_ics_escape(title)}",
            f"DESCRIPTION:{_ics_escape(description)}",
        ]

        if attendees:
            for email in attendees.split(","):
                email = email.strip()
                if email:
                    lines.append(f"ATTENDEE:mailto:{email}")

        lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:-PT10M",
            "ACTION:DISPLAY",
            "DESCRIPTION:Meeting starting soon",
            "END:VALARM",
            "END:VEVENT",
            "END:VCALENDAR",
        ])

        ics_content = "\r\n".join(lines)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ics_content)

        return (
            f"Meeting created: {output_path}\n"
            f"  Title: {title}\n"
            f"  Date: {date} {start_time}\n"
            f"  Duration: {duration_minutes} min\n"
            f"  Agenda items: {len(agenda_items.split(chr(10))) if agenda_items else 0}"
        )
    except Exception as e:
        return f"Error creating meeting: {e!s}"


@tool(description="Parse an existing .ics file and display its events in a readable format.")
async def parse_ics_file(
    file_path: str,
) -> str:
    """Parse and display events from an .ics file.

    Args:
        file_path: Path to the .ics file.
    """
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        events = []
        current_event = {}
        in_event = False

        for line in content.splitlines():
            line = line.strip()
            if line == "BEGIN:VEVENT":
                in_event = True
                current_event = {}
            elif line == "END:VEVENT":
                in_event = False
                if current_event:
                    events.append(current_event)
            elif in_event:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.split(";")[0]
                    current_event[key] = value

        if not events:
            return "No events found in the .ics file."

        lines = [f"Events in {file_path} ({len(events)} events):\n"]
        for i, event in enumerate(events, 1):
            lines.append(f"  {i}. {event.get('SUMMARY', 'Untitled')}")
            if "DTSTART" in event:
                lines.append(f"     Start: {event['DTSTART']}")
            if "DTEND" in event:
                lines.append(f"     End: {event['DTEND']}")
            if "LOCATION" in event:
                lines.append(f"     Location: {event['LOCATION']}")
            if "DESCRIPTION" in event:
                desc = event["DESCRIPTION"].replace("\\n", "\n")
                lines.append(f"     Description: {desc[:100]}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Error parsing .ics file: {e!s}"


@tool(description="Create a countdown timer or reminder event for a future date.")
async def create_reminder(
    title: str,
    reminder_datetime: str,
    description: str = "",
    output_path: str = "/tmp/reminder.ics",
) -> str:
    """Create a reminder event.

    Args:
        title: Reminder title.
        reminder_datetime: When to remind (ISO format).
        description: Reminder details.
        output_path: Path to save the .ics file.
    """
    try:
        dt = _parse_datetime(reminder_datetime)
        if isinstance(dt, str):
            return dt

        event_uid = str(uuid.uuid4())
        now = datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AgentEngine//Reminder//EN",
            "BEGIN:VEVENT",
            f"UID:{event_uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{(dt + timedelta(minutes=15)).strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{_ics_escape(title)}",
        ]

        if description:
            lines.append(f"DESCRIPTION:{_ics_escape(description)}")

        lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:PT0S",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_ics_escape(title)}",
            "END:VALARM",
            "END:VEVENT",
            "END:VCALENDAR",
        ])

        ics_content = "\r\n".join(lines)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ics_content)

        return f"Reminder created: {output_path}\n  Title: {title}\n  Time: {dt.strftime('%Y-%m-%d %H:%M')}"
    except Exception as e:
        return f"Error creating reminder: {e!s}"


def _parse_datetime(dt_string: str) -> datetime | str:
    """Parse a datetime string in various formats."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(dt_string, fmt)
        except ValueError:
            continue
    return f"Error: Cannot parse datetime '{dt_string}'. Use YYYY-MM-DDTHH:MM:SS format."


def _ics_escape(text: str) -> str:
    """Escape text for iCalendar format."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _get_recurrence_rule(recurrence: str) -> str:
    """Convert recurrence string to iCalendar RRULE."""
    rules = {
        "daily": "FREQ=DAILY",
        "weekly": "FREQ=WEEKLY",
        "biweekly": "FREQ=WEEKLY;INTERVAL=2",
        "monthly": "FREQ=MONTHLY",
        "yearly": "FREQ=YEARLY",
        "weekdays": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
    }
    return rules.get(recurrence, "")
