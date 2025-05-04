#!/usr/bin/env python
# chmod +x test_questionnaire_parse.py
# Run this script to test the questionnaire parsing
"""
Script to test parsing of questionnaire content.
This can be run directly to test the parsing logic.
"""

import os
import sys
import re
import django

# Set up Django environment
sys.path.append('/Users/gavinslater/projects/django_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from credit_workflow.models import CreditQuestionnaire

def test_parse_markdown_sections(content):
    """
    Test function to parse markdown content into sections and fields.
    """
    if not content:
        return {}
    
    # Dictionary to store the parsed sections
    sections = {}
    
    # Try to extract sections using different patterns
    
    # First try standard markdown pattern
    section_pattern = r'## ([^\n]+)\s*\n\n([\s\S]*?)(?=\n## |$)'
    section_matches = re.findall(section_pattern, content)
    
    if not section_matches:
        print("No matches found with standard pattern, trying flexible pattern...")
        # Try a more flexible pattern
        section_pattern = r'([A-Z][A-Z\s\']+)\s*\n([\s\S]*?)(?=\n[A-Z][A-Z\s\']+\n|$)'
        section_matches = re.findall(section_pattern, content)
    
    print(f"Found {len(section_matches)} sections")
    
    for section_title, section_content in section_matches:
        print(f"Section: {section_title}")
        
        # Create a normalized section key (no spaces, special chars)
        section_key = section_title.strip().replace("'", "").replace(" ", "_").replace("/", "_").replace("&", "and")
        
        # First try standard markdown for fields
        field_pattern = r'### ([^\n]+)\s*\n([\s\S]*?)(?=\n### |\n\n|$)'
        field_matches = re.findall(field_pattern, section_content)
        
        if not field_matches:
            print(f"  No field matches found with standard pattern, trying flexible pattern...")
            # Try a more flexible pattern
            field_pattern = r'([A-Za-z][^\n:]+):\s*\n([\s\S]*?)(?=\n[A-Za-z][^\n:]+:|$)'
            field_matches = re.findall(field_pattern, section_content)
            
        # Create a dictionary of fields for this section
        fields = {}
        for field_title, field_content in field_matches:
            print(f"  Field: {field_title}")
            # Create a normalized field key (no spaces, special chars)
            field_key = field_title.strip().replace("?", "").replace("(", "").replace(")", "").replace("'", "") \
                                 .replace(",", "").replace(";", "").replace(".", "") \
                                 .replace(" ", "_").replace("/", "_").replace("&", "and")
            fields[field_key] = field_content.strip()
        
        # If no fields were found but there's content, add it as a single field
        if not fields and section_content.strip():
            print(f"  No fields found, adding content as single field")
            fields['content'] = section_content.strip()
        
        # Add this section to the sections dictionary
        sections[section_key] = {
            'title': section_title.strip(),
            'fields': fields
        }
    
    return sections

# Get questionaires from the database
questionnaires = CreditQuestionnaire.objects.all().order_by('-id')[:5]
print(f"Found {len(questionnaires)} recent questionnaires")

for idx, q in enumerate(questionnaires):
    print(f"==== QUESTIONNAIRE {idx+1} (ID: {q.id}) ====")
    if not q.content:
        print("No content")
        continue
        
    # Test our properties
    print("\nModel properties:")
    print(f"business_model_details: {len(q.business_model_details) if q.business_model_details else 'None'}")
    print(f"key_suppliers_customers: {len(q.key_suppliers_customers) if q.key_suppliers_customers else 'None'}")
    print(f"trading_activity_rationale: {len(q.trading_activity_rationale) if q.trading_activity_rationale else 'None'}")
    print(f"trading_policy_governance: {len(q.trading_policy_governance) if q.trading_policy_governance else 'None'}")
    print(f"liquidity_management: {len(q.liquidity_management) if q.liquidity_management else 'None'}")
    
    # Test the parse_markdown_sections function
    print("\nParsed sections:")
    sections = test_parse_markdown_sections(q.content)
    for section_key, section_data in sections.items():
        print(f"{section_key} ({section_data['title']}): {len(section_data['fields'])} fields")
    
    print("\n")

print("Done!")
