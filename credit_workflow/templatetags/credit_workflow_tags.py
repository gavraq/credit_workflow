from django import template
import json
from decimal import Decimal

register = template.Library()

@register.filter(name='mul')
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter(name='div')
def div(value, arg):
    """Divide the value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return ''

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)  # Convert Decimal to string
        return super().default(obj)

@register.filter(name='json')
def to_json(value):
    """Convert a Python object to a JSON string"""
    return json.dumps(value, cls=DecimalEncoder)
