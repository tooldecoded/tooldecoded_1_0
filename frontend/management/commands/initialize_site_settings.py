from django.core.management.base import BaseCommand
from frontend.models import SiteSettings


class Command(BaseCommand):
    help = 'Initialize site settings with default values'

    def handle(self, *args, **options):
        # Get or create the site settings instance
        settings, created = SiteSettings.objects.get_or_create(
            pk=1,
            defaults={
                'show_fair_price_feature': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Successfully created site settings with default values')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Site settings already exist, no changes made')
            )
        
        # Display current settings
        self.stdout.write(f'Current fair price feature status: {"Enabled" if settings.show_fair_price_feature else "Disabled"}')
