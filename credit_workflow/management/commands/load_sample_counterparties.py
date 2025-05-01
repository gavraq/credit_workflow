from django.core.management.base import BaseCommand
from credit_workflow.models import CounterParty

SAMPLE_COUNTERPARTIES = [
    {
        "name": "Africa Resources",
        "cif_number": "AR75319",
        "country_of_risk": "South Africa",
        "business_description": "Mining company with operations across Africa."
    },
    {
        "name": "Asian Commodities Ltd",
        "cif_number": "AC13579",
        "country_of_risk": "Singapore",
        "business_description": "Commodities trading firm specializing in metals and energy."
    },
    {
        "name": "American Steel Inc",
        "cif_number": "AS24680",
        "country_of_risk": "United States",
        "business_description": "Major steel manufacturer with global exports."
    },
    {
        "name": "Euro Metal Trading",
        "cif_number": "ET98765",
        "country_of_risk": "Germany",
        "business_description": "European trading house focused on ferrous and non-ferrous metals."
    },
    {
        "name": "Global Mining Corp",
        "cif_number": "GC12345",
        "country_of_risk": "Australia",
        "business_description": "Diversified mining group with assets in multiple continents."
    },
]

class Command(BaseCommand):
    help = "Load sample counterparties for testing/demo."

    def handle(self, *args, **options):
        for data in SAMPLE_COUNTERPARTIES:
            obj, created = CounterParty.objects.get_or_create(
                cif_number=data["cif_number"],
                defaults=data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {obj}"))
            else:
                self.stdout.write(f"Already exists: {obj}")
