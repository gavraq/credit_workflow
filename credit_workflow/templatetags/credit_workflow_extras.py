from django import template
import re
import markdown

register = template.Library()

@register.filter
def replace(value, arg):
    """
    Replaces all occurrences of the first part of arg in the value with the second part.
    Usage: {{ value|replace:"_: " }}
    This replaces all "_" with " " in the value.
    """
    if ":" not in arg:
        search = arg
        replace_with = " "
    else:
        try:
            search, replace_with = arg.split(":", 1)
        except ValueError:
            return value
    
    return value.replace(search, replace_with)

@register.filter
def replace_underscores(value):
    """
    Formats field keys into readable titles by replacing underscores with spaces 
    and applying proper capitalization.
    """
    if not value:
        return ""
    
    # Replace underscores with spaces
    result = value.replace('_', ' ')
    
    # Handle special words and abbreviations
    result = result.replace('andor', 'and/or')
    result = result.replace('ie ', 'i.e. ')
    result = result.replace('eg ', 'e.g. ')
    result = result.replace(' otc ', ' OTC ')
    result = result.replace(' lme ', ' LME ')
    result = result.replace(' usd ', ' USD ')
    
    # Special handling for common words that should be capitalized
    common_terms = ['lme', 'otc', 'usd', 'eur', 'gbp', 'ifrs', 'asc', 'var', 'pfe', 'impl', 'icbcs']
    words = result.split()
    for i, word in enumerate(words):
        if word.lower() in common_terms:
            words[i] = word.upper()
    
    # Rejoin the words
    result = ' '.join(words)
    
    # Handle special cases for field names
    if result.lower() == 'content':
        return 'Content'
    if result.lower() == 'what metals products do they trade primarily eg lme outrights otc averages loco london gold':
        return 'What Metals/Products Do They Trade Primarily?'
    
    # Capitalize first letter of each word for field names (Title Case)
    result = ' '.join(word.capitalize() for word in result.split())
    
    return result

@register.filter
def split(value, arg):
    """
    Splits the value using the specified separator and returns the list of parts.
    Usage: {{ value|split:"/" }}
    """
    return value.split(arg)

@register.filter
def markdown_to_html(value):
    """
    Converts markdown text to HTML.
    Usage: {{ value|markdown_to_html }}
    """
    if value:
        return markdown.markdown(value)
    return ''

@register.filter
def multiply(value, arg):
    """
    Multiplies the value by the argument.
    Usage: {{ value|multiply:2 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divisibleby(value, arg):
    """
    Returns True if the value is divisible by the argument.
    Usage: {{ value|divisibleby:2 }}
    """
    try:
        return float(value) % float(arg) == 0
    except (ValueError, TypeError):
        return False

@register.filter
def percentage(value, total):
    """
    Calculates what percentage the value is of the total.
    Usage: {{ value|percentage:total }}
    """
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0

@register.filter
def parse_markdown_sections(content):
    """
    Parses markdown content into sections and fields.
    Handles various section and field formats including markdown, plaintext,
    and mixed formats.
    
    Usage: {% with sections=content|parse_markdown_sections %}
    """
    if not content:
        return {}
    
    # Dictionary to store the parsed sections
    sections = {}
    
    # Try to extract sections using different patterns
    
    # Improved pattern: split on any line starting with '## ', regardless of blank lines
    section_pattern = r'^## ([^\n]+)\s*\n([\s\S]*?)(?=^## |\Z)'
    section_matches = re.findall(section_pattern, content, re.MULTILINE)
    
    # If that doesn't work, try a more flexible pattern for section headers without ##
    if not section_matches:
        # Adjusted pattern for uppercase section titles without ## (like "TRADING ACTIVITY")
        section_pattern = r'([A-Z][A-Z\s\'\/#]+)\s*\n([\s\S]*?)(?=\n[A-Z][A-Z\s\'\/#]+\n|$)'
        section_matches = re.findall(section_pattern, content)
    
    # Process each section
    for section_title, section_content in section_matches:
        # Clean up the section title
        section_title = section_title.strip()
        # Remove any ## from the beginning if it's still there
        if section_title.startswith('#'):
            section_title = section_title.lstrip('#').strip()
            
        # Create a normalized section key (no spaces, special chars)
        section_key = section_title.replace("'", "").replace(" ", "_").replace("/", "_").replace("&", "and")
        
        # Try multiple patterns for finding fields within sections
        
        # First try standard markdown for fields with ### headers
        field_pattern = r'### ([^\n]+)\s*\n([\s\S]*?)(?=\n### |\n\n|$)'
        field_matches = re.findall(field_pattern, section_content)
        
        # If that doesn't work, try a pattern for field formats like "Field Title: Content"
        if not field_matches:
            field_pattern = r'([A-Za-z][^\n:]+):\s*\n([\s\S]*?)(?=\n[A-Za-z][^\n:]+:|$)'
            field_matches = re.findall(field_pattern, section_content)
        
        # If that still doesn't work, try another pattern for ## headers used for fields
        if not field_matches:
            field_pattern = r'## ([^\n]+)\s*\n([\s\S]*?)(?=\n## |\n\n|$)'
            field_matches = re.findall(field_pattern, section_content)
            
        # Create a dictionary of fields for this section
        fields = {}
        for field_title, field_content in field_matches:
            # Clean up the field title
            field_title = field_title.strip()
            # Remove any ### from the beginning if it's still there
            if field_title.startswith('#'):
                field_title = field_title.lstrip('#').strip()
                
            # Create a normalized field key (no spaces, special chars)
            field_key = field_title.strip().replace("?", "").replace("(", "").replace(")", "").replace("'", "") \
                                 .replace(",", "").replace(";", "").replace(".", "") \
                                 .replace(" ", "_").replace("/", "_").replace("&", "and")
            fields[field_key] = field_content.strip()
        
        # If no fields were found but there's content, add it as a single field
        if not fields and section_content.strip():
            fields['content'] = section_content.strip()
        
        # Add this section to the sections dictionary
        sections[section_key] = {
            'title': section_title,
            'fields': fields
        }
    
    return sections
