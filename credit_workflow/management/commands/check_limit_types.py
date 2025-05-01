from django.core.management.base import BaseCommand
from credit_workflow.models import LimitType

class Command(BaseCommand):
    help = 'Check and list all LimitType objects in the database'

    def handle(self, *args, **options):
        count = LimitType.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Found {count} LimitType objects in the database.'))
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No LimitType objects found. Creating default limit types...'))
            
            # Original choices from the CreditLimit model
            LIMIT_TYPE_CHOICES = [
                ("TRADING_PRE_SETTLEMENT", "Trading (Pre-Settlement)"),
                ("TRADING_SETTLEMENT", "Trading (Settlement)"),
                ("NOSTRO_PRIMARY", "Nostro (Primary)"),
                ("METAL_LEASE", "Metal Lease"),
                ("TRS", "Total Return Swap (TRS)"),
                ("IM", "Initial Margin (IM)"),
                ("VM", "Variation Margin (VM)"),
                ("SBLC", "Standby Letter of Credit (SBLC)"),
                ("RWA", "Risk-Weighted Assets (RWA)"),
                ("NPL", "Non-Performing Loans (NPL)"),
                ("MLRO", "MLRO Financial Crime Risk"),
                ("IOSCO", "IOSCO"),
                ("VAR", "Value at Risk (VAR)"),
                ("RWR", "Right-Way Risk (RWR)"),
                ("HWWR", "High-Wrong-Way Risk (HWWR)"),
                ("ACCELERATION", "Acceleration"),
            ]
            
            # Create LimitType objects for each choice
            created_count = 0
            for code, name in LIMIT_TYPE_CHOICES:
                limit_type, created = LimitType.objects.get_or_create(
                    code=code,
                    defaults={'name': name}
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created LimitType: {name}'))
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} limit types'))
        else:
            # List all limit types
            self.stdout.write(self.style.NOTICE('Listing all LimitType objects:'))
            for limit_type in LimitType.objects.all().order_by('name'):
                self.stdout.write(f'ID: {limit_type.id}, Code: {limit_type.code}, Name: {limit_type.name}')
