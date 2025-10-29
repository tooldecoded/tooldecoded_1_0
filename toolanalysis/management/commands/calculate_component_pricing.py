from django.core.management.base import BaseCommand
from toolanalysis.pricing_calculator import update_all_component_pricing


class Command(BaseCommand):
    help = 'Calculate component pricing from PriceListings data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', 
            action='store_true', 
            help='Show what would be updated without saving'
        )
        parser.add_argument(
            '--verbose', 
            action='store_true', 
            help='Show detailed output'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be saved')
            )
        
        self.stdout.write('Starting component pricing calculation...')
        
        try:
            stats = update_all_component_pricing(dry_run=dry_run, verbose=verbose)
            
            # Display summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write('PRICING CALCULATION SUMMARY')
            self.stdout.write('='*50)
            self.stdout.write(f"Standalone updates: {stats['standalone_updated']}")
            self.stdout.write(f"Prorated updates: {stats['prorated_updated']}")
            self.stdout.write(f"Skipped (manual override): {stats['skipped']}")
            self.stdout.write(f"Products processed: {stats['products_processed']}")
            
            if stats['errors']:
                self.stdout.write(f"\nErrors encountered: {len(stats['errors'])}")
                for error in stats['errors']:
                    self.stdout.write(
                        self.style.ERROR(f"  - {error}")
                    )
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('\nThis was a dry run. No changes were saved.')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('\nComponent pricing calculation completed successfully!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during pricing calculation: {str(e)}')
            )
            raise
