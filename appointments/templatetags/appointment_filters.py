from django import template
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import datetime

register = template.Library()

@register.filter
def status_color(status):
    """
    Returns the appropriate Bootstrap color class based on appointment status
    """
    color_map = {
        'pending': 'warning',
        'accepted': 'info',
        'paid': 'success',
        'completed': 'success',
        'cancelled': 'danger',
        'rejected': 'secondary'
    }
    return color_map.get(status, 'secondary')

@register.filter
def multiply(value, arg):
    """
    Multiplies the value by the argument
    """
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError):
        return 0

@register.filter
def format_date(value):
    """
    Formats a date consistently with timezone awareness.
    
    Example usage in template:
    {{ appointment.date|format_date }}
    """
    if not value:
        return ""
    
    # If value is a string, try to parse it
    if isinstance(value, str):
        try:
            value = datetime.datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return value
    
    # If value is a datetime, convert to date
    if isinstance(value, datetime.datetime):
        # If USE_TZ is True, ensure the datetime is timezone-aware
        if settings.USE_TZ and timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        # Convert to the current timezone
        value = timezone.localtime(value).date()
    
    # Format date as "Month Day, Year" (e.g., "January 1, 2023")
    return value.strftime("%B %d, %Y")

@register.filter
def format_short_date(value):
    """
    Formats a date in a short format with timezone awareness.
    
    Example usage in template:
    {{ appointment.date|format_short_date }}
    """
    if not value:
        return ""
    
    # If value is a string, try to parse it
    if isinstance(value, str):
        try:
            value = datetime.datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return value
    
    # If value is a datetime, convert to date
    if isinstance(value, datetime.datetime):
        # If USE_TZ is True, ensure the datetime is timezone-aware
        if settings.USE_TZ and timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        # Convert to the current timezone
        value = timezone.localtime(value).date()
    
    # Format date as "MM/DD/YYYY" (e.g., "01/01/2023")
    return value.strftime("%m/%d/%Y") 