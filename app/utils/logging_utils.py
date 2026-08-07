"""Utility module: logging - Common helper functions."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import uuid
from collections.abc import Callable, Generator
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger()
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class LoggingStringUtils:
    """String manipulation utilities."""

    @staticmethod
    def camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case."""
        s1 = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()

    @staticmethod
    def snake_to_camel(name: str) -> str:
        """Convert snake_case to camelCase."""
        parts = name.split('_')
        return parts[0] + ''.join(p.title() for p in parts[1:])

    @staticmethod
    def kebab_to_camel(name: str) -> str:
        """Convert kebab-case to camelCase."""
        parts = name.split('-')
        return parts[0] + ''.join(p.title() for p in parts[1:])

    @staticmethod
    def truncate(text: str, length: int = 100, suffix: str = '...') -> str:
        """Truncate text to specified length."""
        if len(text) <= length:
            return text
        return text[:length - len(suffix)] + suffix

    @staticmethod
    def slugify(text: str) -> str:
        """Convert text to URL slug."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text

    @staticmethod
    def strip_whitespace(text: str) -> str:
        """Remove extra whitespace."""
        return ' '.join(text.split())

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address."""
        if '@' not in email:
            return email
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            return f'{local[0]}***@{domain}'
        return f'{local[0]}***{local[-1]}@{domain}'

    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number."""
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 4:
            return '*' * len(digits)
        return '*' * (len(digits) - 4) + digits[-4:]

    @staticmethod
    def pluralize(count: int, singular: str, plural: str | None = None) -> str:
        """Return singular or plural form."""
        if count == 1:
            return f'{count} {singular}'
        return f'{count} {plural or singular + "s"}'


class LoggingDateUtils:
    """Date and time utilities."""

    @staticmethod
    def now_utc() -> datetime:
        """Get current UTC datetime."""
        return datetime.now(UTC)

    @staticmethod
    def start_of_day(dt: datetime | None = None) -> datetime:
        """Get start of day."""
        dt = dt or datetime.now(UTC)
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def end_of_day(dt: datetime | None = None) -> datetime:
        """Get end of day."""
        dt = dt or datetime.now(UTC)
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    @staticmethod
    def start_of_week(dt: datetime | None = None) -> datetime:
        """Get start of week."""
        dt = dt or datetime.now(UTC)
        start = dt - timedelta(days=dt.weekday())
        return LoggingDateUtils.start_of_day(start)

    @staticmethod
    def end_of_week(dt: datetime | None = None) -> datetime:
        """Get end of week."""
        dt = dt or datetime.now(UTC)
        end = dt + timedelta(days=6 - dt.weekday())
        return LoggingDateUtils.end_of_day(end)

    @staticmethod
    def start_of_month(dt: datetime | None = None) -> datetime:
        """Get start of month."""
        dt = dt or datetime.now(UTC)
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def end_of_month(dt: datetime | None = None) -> datetime:
        """Get end of month."""
        dt = dt or datetime.now(UTC)
        next_month = dt.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        return LoggingDateUtils.end_of_day(last_day)

    @staticmethod
    def humanize_delta(delta: timedelta) -> str:
        """Convert timedelta to human-readable string."""
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f'{total_seconds}s ago'
        if total_seconds < 3600:
            return f'{total_seconds // 60}m ago'
        if total_seconds < 86400:
            return f'{total_seconds // 3600}h ago'
        return f'{total_seconds // 86400}d ago'

    @staticmethod
    def parse_iso(date_str: str) -> datetime | None:
        """Parse ISO format date string."""
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None


class LoggingNumericUtils:
    """Numeric utilities."""

    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value between min and max."""
        return max(min_val, min(max_val, value))

    @staticmethod
    def lerp(a: float, b: float, t: float) -> float:
        """Linear interpolation."""
        return a + (b - a) * t

    @staticmethod
    def percentage(value: float, total: float) -> float:
        """Calculate percentage."""
        if total == 0:
            return 0.0
        return (value / total) * 100

    @staticmethod
    def round_decimal(value: float, places: int = 2) -> Decimal:
        """Round to specified decimal places."""
        d = Decimal(str(value))
        return d.quantize(Decimal('0.' + '0' * places + '1'), rounding=ROUND_HALF_UP)

    @staticmethod
    def format_bytes(size: int) -> str:
        """Format bytes to human-readable string."""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_idx = 0
        size_float = float(size)
        while size_float >= 1024 and unit_idx < len(units) - 1:
            size_float /= 1024
            unit_idx += 1
        return f'{size_float:.1f} {units[unit_idx]}'

    @staticmethod
    def format_currency(amount: float, currency: str = 'USD') -> str:
        """Format currency amount."""
        symbols = {'USD': '$', 'EUR': '\u20ac', 'GBP': '\u00a3', 'JPY': '\u00a5'}
        symbol = symbols.get(currency, currency + ' ')
        return f'{symbol}{amount:,.2f}'

    @staticmethod
    def moving_average(values: list[float], window: int = 5) -> list[float]:
        """Calculate moving average."""
        if window <= 0 or len(values) < window:
            return values
        result = []
        for i in range(len(values) - window + 1):
            result.append(sum(values[i:i + window]) / window)
        return result


class LoggingCollectionUtils:
    """Collection manipulation utilities."""

    @staticmethod
    def chunk(items: list[T], size: int) -> Generator[list[T], None, None]:
        """Split list into chunks."""
        for i in range(0, len(items), size):
            yield items[i:i + size]

    @staticmethod
    def flatten(items: list[list[T]]) -> list[T]:
        """Flatten nested list."""
        return [item for sublist in items for item in sublist]

    @staticmethod
    def unique(items: list[T], key: Callable[[T], Any] | None = None) -> list[T]:
        """Get unique items preserving order."""
        seen = set()
        result = []
        for item in items:
            k = key(item) if key else item
            if k not in seen:
                seen.add(k)
                result.append(item)
        return result

    @staticmethod
    def group_by(items: list[T], key: Callable[[T], K]) -> dict[K, list[T]]:
        """Group items by key function."""
        groups: dict[K, list[T]] = {}
        for item in items:
            k = key(item)
            groups.setdefault(k, []).append(item)
        return groups

    @staticmethod
    def find_first(items: list[T], predicate: Callable[[T], bool]) -> T | None:
        """Find first item matching predicate."""
        for item in items:
            if predicate(item):
                return item
        return None

    @staticmethod
    def partition(items: list[T], predicate: Callable[[T], bool]) -> tuple[list[T], list[T]]:
        """Partition items by predicate."""
        true_list = []
        false_list = []
        for item in items:
            if predicate(item):
                true_list.append(item)
            else:
                false_list.append(item)
        return true_list, false_list


class LoggingCryptoUtils:
    """Cryptographic utilities."""

    @staticmethod
    def generate_uuid() -> str:
        """Generate UUID4 string."""
        return str(uuid.uuid4())

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate random token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_sha256(data: str) -> str:
        """SHA256 hash."""
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def hash_md5(data: str) -> str:
        """MD5 hash."""
        return hashlib.md5(data.encode()).hexdigest()

    @staticmethod
    def base64_encode(data: str) -> str:
        """Base64 encode."""
        return base64.b64encode(data.encode()).decode()

    @staticmethod
    def base64_decode(data: str) -> str:
        """Base64 decode."""
        return base64.b64decode(data.encode()).decode()


class LoggingValidationUtils:
    """Validation utilities."""

    @staticmethod
    def is_empty(value: Any) -> bool:
        """Check if value is empty."""
        if value is None:
            return True
        if isinstance(value, (str, list, dict, tuple, set)):
            return len(value) == 0
        return False

    @staticmethod
    def is_valid_json(data: str) -> bool:
        """Check if string is valid JSON."""
        try:
            json.loads(data)
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format."""
        pattern = r'^https?://[\w.-]+(:\d+)?(/.*)?$'
        return bool(re.match(pattern, url))

    @staticmethod
    def is_valid_uuid(value: str) -> bool:
        """Validate UUID format."""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False
