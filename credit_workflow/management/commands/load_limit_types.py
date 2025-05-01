from django.core.management.base import BaseCommand
from credit_workflow.models import LimitType

class Command(BaseCommand):
    help = 'Creates initial LimitType objects based on the original choices'

    def handle(self, *args, **options):
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
        count = 0
        for code, name in LIMIT_TYPE_CHOICES:
            limit_type, created = LimitType.objects.get_or_create(
                code=code,
                defaults={'name': name}
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'Created LimitType: {name}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} limit types'))
