from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a key
    """
    if dictionary is None:
        return []
    return dictionary.get(key, []) 