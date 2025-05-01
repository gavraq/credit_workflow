from django import template
import re

register = template.Library()

@register.filter
def extract_section(analysis_text, section_title):
    """
    Extract a specific section from the analysis text.
    
    Usage:
        {{ analysis.text|extract_section:"EXECUTIVE SUMMARY" }}
    """
    if not analysis_text or not section_title:
        return ""
    
    # Try to find the section
    pattern = r'## ' + re.escape(section_title) + r'\s*\n(.*?)(?=\n## |$)'
    match = re.search(pattern, analysis_text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    return ""

@register.filter
def split_sections(analysis_text):
    """
    Split the analysis text into sections.
    
    Usage:
        {% for section in analysis.text|split_sections %}
            <h3>{{ section.title }}</h3>
            <div>{{ section.content }}</div>
        {% endfor %}
    """
    if not analysis_text:
        return []
    
    # Split the text by section headings
    sections = []
    pattern = r'## (.*?)\s*\n(.*?)(?=\n## |$)'
    matches = re.finditer(pattern, analysis_text, re.DOTALL)
    
    for match in matches:
        sections.append({
            'title': match.group(1).strip(),
            'content': match.group(2).strip()
        })
    
    return sections
