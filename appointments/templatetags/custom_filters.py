from django import template

register = template.Library()

@register.filter
def split_string(value, arg):
    """Split a string using the provided delimiter and return the specified index"""
    try:
        return value.split(arg)[1]
    except IndexError:
        return ''
